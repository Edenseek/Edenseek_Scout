"""Read-only Audit-Review evidence service (Scout UI, Slice 1).

Assembles the **Consumed-Evidence Manifest** for the currently-configured issue and its current
certified revision: every Publisher S3 object Scout consumes for the generated-vs-approved delta,
with its exact key, load status, size, sha256, version id, revision id, and schema version — plus
permanent audit metadata (``publisher_commit``, ``scout_commit``, ``audit_timestamp``) and a
top-level ``summary`` block the future UI renders directly, without recomputing.

This is the evidentiary core the founder verifies visually: that Publisher evidence is read
correctly and normalized correctly, before any delta is computed or persisted.

Boundaries (Charter §4; Repository Ownership Principle):
  * **Read-only** on ``edenseek-publishing`` — GetObject only, via the least-privilege
    ``edenseek-scout-app`` identity. This module writes nothing anywhere; a per-object failure is
    *recorded* (status ``missing``/``denied``/``error``), never mutating and never masked.
  * Reuses the existing read path (``audit_s3_source``) and the anti-corruption boundary's
    supported-version sets (``review_contract_adapter``); no Publisher-shape logic is duplicated
    here.
  * No LLM / vision / external-service calls; deterministic over the frozen, content-addressed
    Publisher inputs (aside from ``audit_timestamp`` / ``scout_commit``, which are envelope audit
    metadata — like the report's ``created_at`` — not part of any deterministic delta body).

The manifest metadata shape is itself versioned (``manifest_version``) so it can become permanent,
reproducible audit metadata carried into the persisted Scout delta report (Slice 3).
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import audit_s3_source
from review_contract_adapter import (
    SUPPORTED_REVIEW_REPORT_VERSIONS,
    SUPPORTED_PLATFORM_APPROVAL_VERSIONS,
    ReviewContractError,
)
from delta_auditor import run_delta_audit, serialize_delta_report
from logging_config import logger

MANIFEST_VERSION = "v1"
AUDIT_REVIEW_VERSION = "v1"

# The version of the EVALUATION rules that turn delta numbers into severity-tagged findings
# (``_project_findings``). Bump when the PASS/WARNING/FAIL/INFO thresholds or rules change; it is
# one axis of the comparability contract (see docs/architecture/SCOUT_REPORT_INDEX.md).
EVALUATION_VERSION = "v1"

# Finding severities the UI renders at-a-glance.
PASS, WARNING, FAIL, INFO = "PASS", "WARNING", "FAIL", "INFO"
_HERE = Path(__file__).resolve().parent


class AuditReviewError(Exception):
    """Raised only for whole-manifest configuration errors (unconfigured source, unresolvable
    pointer). Per-object read failures are recorded in the manifest, not raised."""


def _derive_review_id(published_revision_id):
    """``review_id = "rev_" + <sha256 of published revision>[:12]`` — the same deterministic
    derivation Scout uses to address the ``reviews/{review_id}/`` certification artifacts."""
    return "rev_" + published_revision_id.split("_", 1)[1][:12]


def _scout_commit():
    """Scout's own git HEAD (with a ``+dirty`` suffix if the tree has uncommitted changes) — the
    code version that produced this manifest, for report reproducibility. Fail-soft to ``None``
    (a missing git context must not break a read-only endpoint)."""
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=_HERE,
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if not sha:
            return None
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=_HERE,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return None


def _schema_version(role, parsed):
    """Extract the Publisher-declared schema version for a parsed object, or ``None``. The
    content-addressed processing snapshot has no schema version — its identity is its revision
    hash, captured separately as ``revision_id``."""
    if not isinstance(parsed, dict):
        return None
    return {
        "approved_pointer": parsed.get("published_pointer_version"),
        "review_report": parsed.get("review_report_version"),
        "platform_approval": parsed.get("platform_approval_version"),
    }.get(role)


def _gather_evidence(client):
    """Probe the four consumed objects once and return ``(manifest, parsed_by_role)``.

    ``parsed_by_role`` holds the parsed JSON for the objects we parse (pointer, review_report,
    platform_approval) so a downstream delta reuses them without re-fetching. Read-only; per-object
    failures are recorded in the manifest, not raised.
    """
    bucket = os.getenv(audit_s3_source.BUCKET_ENV)
    prefix = os.getenv(audit_s3_source.PREFIX_ENV)
    if not bucket or not prefix:
        raise AuditReviewError(
            "Approved-Dataset S3 source is not configured: set "
            f"{audit_s3_source.BUCKET_ENV} and {audit_s3_source.PREFIX_ENV}.")

    segments = audit_s3_source._require_approved_prefix(prefix)
    normalized = "/".join(segments)
    issue_root = normalized[: -len("/approved")]
    _series_id, issue_id = audit_s3_source._derive_identity_tail(segments)

    client = client or audit_s3_source.s3_client()

    # Resolve the mutable pointer (fail-loud — without it there is no revision to review).
    try:
        pointer = audit_s3_source.resolve_current_revision(client)
    except audit_s3_source.ScoutS3SourceError as e:
        raise AuditReviewError(f"Unable to resolve the current certified revision: {e}") from e

    published_revision_id = pointer["revision_id"]
    review_id = _derive_review_id(published_revision_id)

    # The four objects Scout consumes for the generated-vs-approved delta, in read order.
    roles = [
        ("approved_pointer", pointer["key"], published_revision_id, True),
        ("processing_snapshot", pointer["revision_key"], published_revision_id, False),
        ("review_report", f"{issue_root}/reviews/{review_id}/review_report.json", review_id, True),
        ("platform_approval", f"{issue_root}/reviews/{review_id}/platform_approval.json", review_id, True),
    ]

    objects = []
    parsed_by_role = {}
    for role, key, revision_id, parse in roles:
        probe = audit_s3_source.probe_object(client, bucket, key)
        parsed = None
        if probe["status"] == "read" and parse:
            try:
                parsed = json.loads(probe["body"])
                parsed_by_role[role] = parsed
            except json.JSONDecodeError:
                parsed = None
        objects.append({
            "role": role,
            "key": key,
            "status": probe["status"],
            "size": probe["size"],
            "sha256": probe["sha256"],
            "version_id": probe["version_id"],
            "revision_id": revision_id,
            "schema_version": _schema_version(role, parsed),
        })

    # --- summary health block (permanent; rendered directly, never recomputed) ---
    loaded = sum(1 for o in objects if o["status"] == "read")
    expected = len(objects)
    rr_ok = _schema_version("review_report", parsed_by_role.get("review_report")) \
        in SUPPORTED_REVIEW_REPORT_VERSIONS
    pa_ok = _schema_version("platform_approval", parsed_by_role.get("platform_approval")) \
        in SUPPORTED_PLATFORM_APPROVAL_VERSIONS
    audit_ready = (loaded == expected) and rr_ok and pa_ok

    rr_prov = (parsed_by_role.get("review_report") or {}).get("provenance") or {}
    publisher_commit = rr_prov.get("published_revision_id") or published_revision_id
    # Full issue ownership chain, authoritatively from the Review Record (falls back to the
    # configured prefix's issue segment). Lets the report index carry publisher/title/series/issue.
    issue_identity = dict((parsed_by_role.get("review_report") or {}).get("issue_identity") or {})
    issue_identity.setdefault("issue_id", issue_id)

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "audit_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scout_commit": _scout_commit(),
        "publisher_commit": publisher_commit,
        "issue_id": issue_id,
        "issue_identity": issue_identity,
        "review_id": review_id,
        "bucket": bucket,
        "objects": objects,
        "summary": {
            "objects_expected": expected,
            "objects_loaded": loaded,
            "objects_missing": expected - loaded,
            "publisher_mutation": "none",  # GetObject-only identity; writes IAM-denied (Phase B v5)
            "audit_ready": audit_ready,
        },
        "publisher_provenance": {
            "chain_id": rr_prov.get("chain_id"),
            "published_at": rr_prov.get("published_at"),
            "initiating_user": rr_prov.get("initiating_user"),
        },
    }
    logger.info(
        "Audit-review evidence manifest: issue=%s review_id=%s loaded=%d/%d audit_ready=%s",
        issue_id, review_id, loaded, expected, audit_ready,
    )
    return manifest, parsed_by_role


def build_evidence_manifest(client=None):
    """Build the read-only Consumed-Evidence Manifest for the configured issue + current revision.

    Resolves the published pointer, derives ``review_id``, and probes the four Publisher objects
    Scout consumes for the delta (approved pointer, processing snapshot, review report, platform
    approval). Returns a manifest dict with permanent audit metadata + a ``summary`` health block.
    Fail-loud only on whole-manifest config/resolution errors; per-object issues are recorded.
    """
    client = client or audit_s3_source.s3_client()
    manifest, _parsed = _gather_evidence(client)
    return manifest


def _state_comparison(delta, manifest):
    """Publisher-certified state (verbatim) beside Scout's independent canonical view — the two
    are shown side by side, never merged. Scout sets no state; it reports its own measurement."""
    pcs = delta.get("publisher_certified_state", {}) or {}
    readiness = pcs.get("platform_readiness") or {}
    geo = delta.get("geometry_delta", {}) or {}
    meta = delta.get("metadata_delta", {}) or {}
    return {
        "publisher_certified": {
            "canonical_dataset_state": pcs.get("canonical_dataset_state"),
            "passes_integrity": readiness.get("passes_integrity"),
            "geometry_artifact_count": readiness.get("geometry_artifact_count"),
            "metadata_artifact_count": readiness.get("metadata_artifact_count"),
            "hard_failures": readiness.get("hard_failures"),
            "warnings": readiness.get("warnings"),
        },
        "scout_canonical": {
            "applicability": delta.get("applicability"),
            "review_id": delta.get("review_id"),
            "published_revision_id": delta.get("provenance", {}).get("published_revision_id"),
            "generated_snapshot_revision_id":
                delta.get("provenance", {}).get("generated_snapshot_revision_id"),
            "approved_panel_count": geo.get("approved_panel_count"),
            "geometry_applicable": geo.get("applicable"),
            "metadata_applicable": meta.get("applicable"),
            "metadata_compared_artifacts": meta.get("compared_artifact_count"),
            "source_versions": delta.get("provenance", {}).get("source_versions"),
            "audit_ready": manifest["summary"]["audit_ready"],
        },
    }


def _delta_summary(delta):
    """Compact, human-readable rollup of the delta the UI can render without walking the full report."""
    geo = delta.get("geometry_delta", {}) or {}
    meta = delta.get("metadata_delta", {}) or {}
    if meta.get("applicable") and meta.get("compared_artifact_count"):
        meta_summary = {"status": "computed", "compared": meta.get("compared_artifact_count"),
                        "acceptance_rate": meta.get("acceptance_rate"),
                        "edit_rate": meta.get("edit_rate"), "addition_rate": meta.get("addition_rate")}
    elif meta.get("applicable"):
        meta_summary = {"status": "abstained",
                        "reason": "schema_version_mismatch",
                        "mismatched_artifacts": len(meta.get("schema_version_mismatch_artifact_ids", []))}
    else:
        meta_summary = {"status": "not_applicable", "reason": meta.get("reason")}
    geo_summary = ({"status": "not_applicable", "reason": geo.get("reason")} if not geo.get("applicable")
                   else {"status": "computed", "precision": geo.get("precision"),
                         "recall": geo.get("recall"), "split_rate": geo.get("split_rate"),
                         "merge_rate": geo.get("merge_rate"),
                         "missing": len(geo.get("missing_page_artifact_ids", [])),
                         "spread_missing": len(geo.get("spread_missing_artifact_ids", [])),
                         "false": geo.get("false_count")})
    return {"geometry": geo_summary, "metadata": meta_summary,
            "correction_ledger_entries": len(delta.get("correction_ledger", []))}


def _project_findings(manifest, delta, adapter_error, delta_sha):
    """Deterministic projection of the audit into severity-tagged findings (PASS/WARNING/FAIL/INFO).

    Advisory only: Scout reports health signals for at-a-glance verification; it gates nothing.
    """
    findings = []

    def add(code, severity, title, detail):
        findings.append({"code": code, "severity": severity, "title": title, "detail": detail})

    s = manifest["summary"]
    missing = [o["role"] for o in manifest["objects"] if o["status"] != "read"]
    add("evidence.loaded", PASS if not missing else FAIL, "Publisher evidence loaded",
        f"{s['objects_loaded']}/{s['objects_expected']} objects read"
        + (f"; not read: {', '.join(missing)}" if missing else ""))

    add("publisher.mutation", PASS, "No mutation of edenseek-publishing",
        "Scout read the Publisher repository GetObject-only; writes are IAM-denied.")

    if adapter_error is not None:
        add("contract.adapted", FAIL, "Review Record rejected at the anti-corruption boundary",
            str(adapter_error))
        return findings  # no delta to project further

    add("contract.adapted", PASS, "Review Record adapted through the anti-corruption boundary",
        "Contract versions are supported; Scout normalized the Publisher shapes without reinterpretation.")

    pcs = delta.get("publisher_certified_state", {}) or {}
    readiness = pcs.get("platform_readiness") or {}
    integ = readiness.get("passes_integrity")
    add("publisher.certified_state", INFO if integ else WARNING, "Publisher certified state (verbatim)",
        f"state={pcs.get('canonical_dataset_state')}, passes_integrity={integ} "
        "(carried verbatim; Scout does not gate or re-derive this).")

    meta = delta.get("metadata_delta", {}) or {}
    if meta.get("applicable") and meta.get("compared_artifact_count"):
        add("metadata.comparability", PASS, "Metadata delta computed",
            f"compared {meta['compared_artifact_count']} artifacts within a single schema version.")
    elif meta.get("applicable"):
        n = len(meta.get("schema_version_mismatch_artifact_ids", []))
        add("metadata.comparability", WARNING, "Metadata delta abstained (schema-version skew)",
            f"generated vs approved enrichment schema versions differ for {n} artifacts; Scout will "
            "not compare across the boundary. A true historical fact for this immutable revision.")
    else:
        add("metadata.comparability", INFO, "Metadata delta not applicable",
            f"reason={meta.get('reason')}.")

    geo = delta.get("geometry_delta", {}) or {}
    if geo.get("applicable"):
        add("geometry.delta", INFO, "Geometry delta computed",
            f"precision {geo.get('precision')}, recall {geo.get('recall')}, "
            f"missing {len(geo.get('missing_page_artifact_ids', []))}, "
            f"spread-missing {len(geo.get('spread_missing_artifact_ids', []))}, "
            f"false {geo.get('false_count')}.")
        if geo.get("false_count"):
            add("geometry.false_panels", WARNING, "Automated panels absent from approval",
                f"{geo['false_count']} generated panel(s) had no matching approved panel (precision gap).")
    else:
        add("geometry.delta", INFO, "Geometry delta not applicable", f"reason={geo.get('reason')}.")

    add("delta.deterministic", PASS, "Delta serialization is byte-deterministic",
        f"canonical serialization sha256={delta_sha[:12]}…")
    return findings


def build_audit_review(client=None):
    """Full read-only audit-review view: evidence manifest + live delta + Publisher/Scout state
    side by side + severity findings + the delta report in human-readable rollup form.

    Runs the SAME deterministic ``run_delta_audit`` used in the Phase-B certification, over the live
    Review Record + Platform Approval. Read-only; computes and persists nothing (persistence is
    Slice 3). Fail-loud only on whole-view config/resolution errors.
    """
    client = client or audit_s3_source.s3_client()
    manifest, parsed = _gather_evidence(client)

    review_report = parsed.get("review_report")
    platform_approval = parsed.get("platform_approval")

    delta = None
    delta_sha = None
    adapter_error = None
    if review_report is not None:
        try:
            delta = run_delta_audit(review_report, platform_approval)
            delta_sha = hashlib.sha256(serialize_delta_report(delta)).hexdigest()
        except ReviewContractError as e:
            adapter_error = e
    else:
        adapter_error = ReviewContractError(
            "review_report was not loaded (see evidence manifest object statuses)")

    findings = _project_findings(manifest, delta, adapter_error, delta_sha or "")
    view = {
        "audit_review_version": AUDIT_REVIEW_VERSION,
        "audit_timestamp": manifest["audit_timestamp"],
        "scout_commit": manifest["scout_commit"],
        "publisher_commit": manifest["publisher_commit"],
        "issue_id": manifest["issue_id"],
        "review_id": manifest["review_id"],
        "evidence": manifest,
        "findings": findings,
        "state_comparison": _state_comparison(delta, manifest) if delta else None,
        "delta_summary": _delta_summary(delta) if delta else None,
        "delta_report": delta,
        "delta_report_sha256": delta_sha,
    }
    worst = (FAIL if any(f["severity"] == FAIL for f in findings)
             else WARNING if any(f["severity"] == WARNING for f in findings) else PASS)
    logger.info("Audit-review view: review_id=%s findings=%d worst=%s delta=%s",
                manifest["review_id"], len(findings), worst, "yes" if delta else "no")
    return view


def _load_dotenv(path=None):
    """Minimal .env loader for the CLI verification path only (the app/systemd supplies env)."""
    path = Path(path or (_HERE / ".env"))
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    # Verification entry point: `python audit_review.py` prints the full audit-review view;
    # `python audit_review.py --evidence-only` prints just the consumed-evidence manifest.
    import sys as _sys
    _load_dotenv()
    os.environ.pop("AWS_PROFILE", None)
    _view = (build_evidence_manifest() if "--evidence-only" in _sys.argv[1:]
             else build_audit_review())
    print(json.dumps(_view, indent=2, ensure_ascii=False))
