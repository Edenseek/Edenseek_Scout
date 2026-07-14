"""Deterministic Scout report publisher — write path to the Scout Repository
(``edenseek-scout``) at the frozen R1 Object-Key Contract (Week 10 Day 15).

Day 14 gave Scout a read-only path from the canonical Approved-Dataset. This
module adds the missing *publication* path: it takes the report blocks the
existing audit engine already produces (``result['blocks']`` — see
``dataset_auditor.run_dataset_audit`` / ``audit_reports``) and writes them to the
Scout Repository at the two — and only two — addressing roles defined by the
frozen Object-Key Contract (R1, ``docs/architecture/edenseek_scout_repository.md``):

  * Latest-state:  ``{issue}/reports/{artifact_type}.json``          (overwrite)
  * History:       ``{issue}/history/{artifact_type}_{run_seq}.json``  (append-only)

``run_seq`` is a per-(issue, artifact_type) monotonic, zero-padded sequence — the
successor of the highest existing sequence — so a history object is always a new,
never-before-targeted key (append-only by construction; existing snapshots are
never overwritten). No key carries a version or timestamp token; the wall-clock
time lives only as a field *inside* the object (R1).

Boundaries (Charter §4; Repository Ownership Principle):
  * Scout writes ONLY to the Scout Repository (``edenseek-scout``), and only under
    the configured per-issue ownership chain. It never writes to the Publishing
    Repository — this module has no knowledge of that bucket.
  * No LLM / vision / external-service calls; deterministic over frozen inputs.

Fail-loud: if the Scout Repository write target is not configured, the prefix is
not a valid issue ownership chain, or any write fails, this raises
``ScoutReportPublishError`` rather than falling back to local files.
"""
import json
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger
import audit_reports

# Explicit Scout Repository write-target configuration (no defaults that would
# silently write somewhere other than the provisioned edenseek-scout bucket).
BUCKET_ENV = "SCOUT_REPO_S3_BUCKET"   # the edenseek-scout bucket
PREFIX_ENV = "SCOUT_REPO_S3_PREFIX"   # issue ownership chain: publishers/.../issues/{issue_id}
REGION_ENV = "SCOUT_REPO_S3_REGION"
DEFAULT_REGION = "us-west-2"

# Zero-padded width for the history run_seq token (e.g. 000001).
RUN_SEQ_WIDTH = 6

# Scout software version stamped into the Scout Report provenance.
SCOUT_VERSION = "0.4.0"
# Consolidated Scout Report envelope schema version and artifact name. This
# envelope is the canonical, primary Scout Report artifact — the beginning of the
# Scout -> Edenseek governance/reporting contract (see REPORT_SPECIFICATION.md).
SCOUT_REPORT_VERSION = "v1"
SCOUT_REPORT_TYPE = "scout_report"

# Report-family blocks whose ``findings`` roll up into the consolidated report.
_FINDING_SOURCES = ("dataset", "character", "dialogue", "retrieval")

_ADVISORY = (
    "> Read-only advisory report. Scout inspects, scores, and recommends only; it does not "
    "modify canonical data, approve metadata, or bypass publisher review (Charter §4)."
)


class ScoutReportPublishError(Exception):
    """Raised when the Scout Repository write target is unconfigured or a write fails."""


def is_configured():
    """True only when an explicit Scout Repository write target is configured."""
    return bool(os.getenv(BUCKET_ENV) and os.getenv(PREFIX_ENV))


def _s3_client(region):
    # Isolated for test injection. Credentials resolve through the standard AWS
    # chain — the read/write ``edenseek-scout-app`` identity (sole writer to
    # edenseek-scout; see Repository Ownership Principle).
    return boto3.client("s3", region_name=region)


def _require_issue_prefix(prefix):
    """Enforce the write prefix is a per-issue ownership chain ending at the issue.

    The Scout Repository mirrors the Publishing Repository ownership chain exactly
    (``publishers/{publisher_id}/.../issues/{issue_id}``). Refusing anything else
    guarantees derived artifacts land under the issue that owns them. Returns
    ``(normalized_prefix, issue_id)``.
    """
    segments = prefix.strip().strip("/").split("/")
    try:
        issue_id = segments[segments.index("issues") + 1]
    except (ValueError, IndexError):
        raise ScoutReportPublishError(
            "Refusing Scout Repository prefix without an 'issues/{issue_id}' chain: "
            f"{prefix!r}"
        )
    if "publishers" not in segments or segments[-1] != issue_id:
        raise ScoutReportPublishError(
            "Scout Repository prefix must be the issue ownership-chain root "
            f"'publishers/.../issues/{{issue_id}}': {prefix!r}"
        )
    return "/".join(segments), issue_id


def _serialize(report_type, block, generated_at, dataset_id, issue_id, run_seq=None):
    """Deterministic JSON envelope for one report.

    Wall-clock (``generated_at``) is carried as a field inside the object, never
    in the key (R1). ``sort_keys`` makes the byte output stable across runs for
    identical content.
    """
    envelope = {
        "artifact_type": report_type,
        "dataset_id": dataset_id,
        "issue_id": issue_id,
        "generated_at": generated_at,
        "block": block,
    }
    if run_seq is not None:
        envelope["run_seq"] = run_seq
    return json.dumps(envelope, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"


def _next_run_seq(client, bucket, history_prefix, report_type):
    """Successor of the highest existing zero-padded run_seq for (issue, artifact_type).

    Lists ``{history_prefix}/{report_type}_*`` and returns ``max + 1`` (1 when
    none exist). The all-digits guard disambiguates report types whose names are
    prefixes of others (e.g. ``retrieval`` vs ``retrieval_blockers``).
    """
    token_prefix = f"{history_prefix}/{report_type}_"
    highest = 0
    continuation = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": token_prefix}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        try:
            resp = client.list_objects_v2(**kwargs)
        except (ClientError, BotoCoreError) as e:
            raise ScoutReportPublishError(
                f"Unable to enumerate history for {report_type!r} under "
                f"s3://{bucket}/{history_prefix}/: {e}"
            ) from e
        for obj in resp.get("Contents", []):
            name = obj["Key"].rsplit("/", 1)[-1]
            if not name.startswith(f"{report_type}_") or not name.endswith(".json"):
                continue
            stem = name[len(report_type) + 1 : -len(".json")]
            if stem.isdigit():
                highest = max(highest, int(stem))
        if resp.get("IsTruncated"):
            continuation = resp.get("NextContinuationToken")
        else:
            break
    return highest + 1


def publish_reports(result, generated_at, report_types=None, client=None):
    """Publish audit report blocks to the Scout Repository at the frozen R1 keys.

    For each report type this writes both addressing roles:
      * latest-state ``{issue}/reports/{artifact_type}.json`` (overwritten in place;
        prior runs are retained as S3 noncurrent versions), and
      * an immutable history snapshot ``{issue}/history/{artifact_type}_{run_seq}.json``
        at a fresh ``run_seq`` (append-only; never overwrites an existing key).

    Reuses the report blocks the audit engine already generated (no re-computation)
    and the report-type set from ``audit_reports``. Read/write only within the
    configured ``edenseek-scout`` issue chain. Fail-loud when unconfigured or a
    write fails. Returns ``{report_type: {"latest": key, "history": key}}``.
    """
    bucket = os.getenv(BUCKET_ENV)
    prefix = os.getenv(PREFIX_ENV)
    if not bucket or not prefix:
        raise ScoutReportPublishError(
            "Scout Repository write target is not configured: set "
            f"{BUCKET_ENV} and {PREFIX_ENV} (there is no local fallback)."
        )

    region = os.getenv(REGION_ENV, DEFAULT_REGION)
    issue_prefix, issue_id = _require_issue_prefix(prefix)
    dataset_id = result["dataset_id"]
    blocks = result["blocks"]
    report_types = report_types or list(audit_reports.REPORT_FILES.keys())

    client = client or _s3_client(region)
    reports_prefix = f"{issue_prefix}/reports"
    history_prefix = f"{issue_prefix}/history"

    published = {}
    for report_type in report_types:
        block = blocks[report_type]
        run_seq = _next_run_seq(client, bucket, history_prefix, report_type)
        seq_token = f"{run_seq:0{RUN_SEQ_WIDTH}d}"

        latest_key = f"{reports_prefix}/{report_type}.json"
        history_key = f"{history_prefix}/{report_type}_{seq_token}.json"

        latest_body = _serialize(report_type, block, generated_at, dataset_id, issue_id)
        history_body = _serialize(report_type, block, generated_at, dataset_id, issue_id, run_seq)

        try:
            # Immutable history snapshot first, at a fresh (max+1) key so it can
            # never overwrite an existing snapshot; then overwrite latest-state.
            client.put_object(
                Bucket=bucket, Key=history_key, Body=history_body,
                ContentType="application/json",
            )
            client.put_object(
                Bucket=bucket, Key=latest_key, Body=latest_body,
                ContentType="application/json",
            )
        except (ClientError, BotoCoreError) as e:
            raise ScoutReportPublishError(
                f"Unable to publish Scout report {report_type!r} to "
                f"s3://{bucket}/{issue_prefix}/: {e}"
            ) from e

        published[report_type] = {"latest": latest_key, "history": history_key}

    logger.info(
        f"Published {len(published)} Scout report(s) to s3://{bucket}/{issue_prefix}/ "
        "(latest-state reports/ + immutable history/ per R1 Object-Key Contract)"
    )
    return published


# --------------------------------------------------------------------------- #
# Consolidated Scout Report (Week 10 Day 18) — the canonical, provenance-bearing
# artifact tied to the exact Publisher Approved Dataset revision analyzed.
# --------------------------------------------------------------------------- #

def _dumps(obj):
    """Deterministic UTF-8 JSON bytes (stable across runs for identical content)."""
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"


def _aggregate_findings(blocks):
    """Roll up per-report findings into one consolidated, source-tagged list."""
    findings = []
    for source in _FINDING_SOURCES:
        for f in blocks.get(source, {}).get("findings", []):
            findings.append({
                "source": source,
                "artifact_id": f.get("artifact_id"),
                "packet_id": f.get("packet_id"),
                "issue": f.get("issue") or f.get("gap"),
                "severity": f.get("severity"),
                "recommendation": f.get("recommendation"),
            })
    return findings


def _distinct_recommendations(findings):
    """Order-preserving distinct recommendation strings from the findings."""
    recs, seen = [], set()
    for f in findings:
        rec = f.get("recommendation")
        if rec and rec not in seen:
            seen.add(rec)
            recs.append(rec)
    return recs


def _evidence_references(blocks):
    """Retrieval-evidence summary the review layer consumes as supporting evidence."""
    retrieval = blocks.get("retrieval", {})
    coverage = blocks.get("retrieval_blockers", {}).get("packet_coverage", {})
    return {
        "retrieval_packets_evaluated": retrieval.get("packets_evaluated", 0),
        "retrieval_artifacts_referenced": retrieval.get("artifacts_referenced", 0),
        "retrieval_coverage_percent": coverage.get("coverage_percent"),
        "retrieval_readiness_score": retrieval.get("retrieval_readiness_score"),
        "highest_leverage_failure": blocks.get("highest_leverage", {}).get("highest_leverage_failure"),
    }


def build_scout_report(result, generated_at, provenance, issue_id, run_seq):
    """Assemble the consolidated Scout Report envelope (pure projection over blocks).

    Ties the deterministic audit to the exact Publisher Approved Dataset revision
    via ``provenance``. Deterministic for identical inputs (aside from
    ``created_at``/``run_seq``, which version the artifact).
    """
    blocks = result["blocks"]
    dataset_block = blocks.get("dataset", {})
    revision_id = (provenance or {}).get("publisher_revision_id") or "local"
    report_id = f"scout::{issue_id}::{revision_id}::run{run_seq:0{RUN_SEQ_WIDTH}d}"
    findings = _aggregate_findings(blocks)
    return {
        "report_version": SCOUT_REPORT_VERSION,
        "report_type": SCOUT_REPORT_TYPE,
        "report_id": report_id,
        "scout_version": SCOUT_VERSION,
        "created_at": generated_at,
        "dataset_id": result["dataset_id"],
        "issue_id": issue_id,
        "run_seq": run_seq,
        "provenance": provenance or {"source": "local_or_explicit_dir"},
        "audit_results": {
            "quality_score": result["quality_score"],
            "scores": result["scores"],
            "artifact_count": result["artifact_count"],
            "coverage": dataset_block.get("coverage", {}),
            "completeness": dataset_block.get("completeness", {}),
        },
        "findings": findings,
        "recommendations": _distinct_recommendations(findings),
        "evidence_references": _evidence_references(blocks),
    }


def render_scout_report_md(report):
    """Human-readable Markdown rendering of the consolidated Scout Report."""
    prov = report.get("provenance", {})
    ar = report["audit_results"]
    lines = [
        f"# Scout Report — {report['dataset_id']}",
        "",
        _ADVISORY,
        "",
        f"- Report ID: `{report['report_id']}`",
        f"- Scout version: {report['scout_version']}",
        f"- Created: {report['created_at']}",
        "",
        "## Source (Publisher Approved Dataset revision)",
        f"- Pointer key: `{prov.get('publisher_pointer_key')}`",
        f"- Revision ID: `{prov.get('publisher_revision_id')}`",
        f"- Revision key: `{prov.get('publisher_revision_key')}`",
        "",
        "## Audit Results",
        f"- Overall quality score: {ar['quality_score']}/100",
        f"- Artifacts: {ar['artifact_count']}",
    ]
    for k, v in ar.get("scores", {}).items():
        lines.append(f"- {k}: {v}")
    cov = ar.get("coverage", {})
    if cov:
        lines.append(
            f"- Coverage — approved {cov.get('approved')}/{cov.get('total')}, "
            f"reviewed {cov.get('reviewed')}/{cov.get('total')}, "
            f"locked {cov.get('locked')}/{cov.get('total')}"
        )
    lines += ["", f"## Findings ({len(report['findings'])})"]
    if report["findings"]:
        for f in report["findings"]:
            ref = f.get("artifact_id") or f.get("packet_id")
            prefix = f"`{ref}` — " if ref else ""
            lines.append(f"- **[{f.get('severity')}]** ({f.get('source')}) {prefix}{f.get('issue')}")
    else:
        lines.append("- None")
    lines += ["", "## Recommendations"]
    lines += [f"- {r}" for r in report["recommendations"]] or ["- None"]
    lines += ["", "```json", json.dumps(report, indent=2, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


def _put(client, bucket, key, body, content_type):
    try:
        client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    except (ClientError, BotoCoreError) as e:
        raise ScoutReportPublishError(
            f"Unable to publish Scout Report object s3://{bucket}/{key}: {e}"
        ) from e


def _verify_readback(client, bucket, key, expected_body):
    """Read the just-written object back and assert it matches byte-for-byte."""
    try:
        got = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except (ClientError, BotoCoreError) as e:
        raise ScoutReportPublishError(
            f"Unable to read back persisted Scout Report s3://{bucket}/{key}: {e}"
        ) from e
    if got != expected_body:
        raise ScoutReportPublishError(
            f"Persisted Scout Report at s3://{bucket}/{key} does not match the "
            "locally produced deterministic report (round-trip mismatch)."
        )


def publish_scout_report(result, generated_at, provenance=None, client=None):
    """Persist the consolidated Scout Report to the Scout Repository and verify it.

    Writes the canonical machine-readable ``scout_report.json`` (latest + immutable
    history) and a human-readable ``scout_report.md`` alongside it, at the frozen R1
    keys, then reads each object back and asserts it matches the locally produced
    bytes. Write-only within the configured ``edenseek-scout`` issue chain; never
    touches the Publisher Repository. Fail-loud when unconfigured, a write fails, or
    a read-back mismatches. Returns the report id and the keys written.
    """
    bucket = os.getenv(BUCKET_ENV)
    prefix = os.getenv(PREFIX_ENV)
    if not bucket or not prefix:
        raise ScoutReportPublishError(
            "Scout Repository write target is not configured: set "
            f"{BUCKET_ENV} and {PREFIX_ENV} (there is no local fallback)."
        )

    region = os.getenv(REGION_ENV, DEFAULT_REGION)
    issue_prefix, issue_id = _require_issue_prefix(prefix)
    client = client or _s3_client(region)
    reports_prefix = f"{issue_prefix}/reports"
    history_prefix = f"{issue_prefix}/history"

    run_seq = _next_run_seq(client, bucket, history_prefix, SCOUT_REPORT_TYPE)
    seq_token = f"{run_seq:0{RUN_SEQ_WIDTH}d}"

    report = build_scout_report(result, generated_at, provenance, issue_id, run_seq)
    json_body = _dumps(report)
    md_body = (render_scout_report_md(report)).encode("utf-8")

    keys = {
        "latest_json": f"{reports_prefix}/{SCOUT_REPORT_TYPE}.json",
        "history_json": f"{history_prefix}/{SCOUT_REPORT_TYPE}_{seq_token}.json",
        "latest_md": f"{reports_prefix}/{SCOUT_REPORT_TYPE}.md",
        "history_md": f"{history_prefix}/{SCOUT_REPORT_TYPE}_{seq_token}.md",
    }

    # Immutable history first (fresh run_seq key — never overwrites), then latest.
    _put(client, bucket, keys["history_json"], json_body, "application/json")
    _put(client, bucket, keys["history_md"], md_body, "text/markdown")
    _put(client, bucket, keys["latest_json"], json_body, "application/json")
    _put(client, bucket, keys["latest_md"], md_body, "text/markdown")

    # Verify each persisted object reads back identical to what we produced.
    _verify_readback(client, bucket, keys["history_json"], json_body)
    _verify_readback(client, bucket, keys["history_md"], md_body)
    _verify_readback(client, bucket, keys["latest_json"], json_body)
    _verify_readback(client, bucket, keys["latest_md"], md_body)

    logger.info(
        f"Published + verified consolidated Scout Report {report['report_id']} to "
        f"s3://{bucket}/{issue_prefix}/ (revision "
        f"{(provenance or {}).get('publisher_revision_id')})"
    )
    return {"report_id": report["report_id"], "run_seq": run_seq, "keys": keys}
