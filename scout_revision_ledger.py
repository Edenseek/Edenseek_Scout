"""Durable processed-revision / idempotency ledger for the Scout delta-audit agent (Increment 2).

Records, per issue, which eligible Publisher revisions have been audited-and-persisted by Scout —
and which attempts failed — so the same publication is not repeatedly audited, retries are safe, and
reconciliation can find unaudited eligible revisions. Stored in ``edenseek-scout`` only.

Key idea: a ledger entry is keyed by ``{published_revision_id}@{context_fingerprint}`` — the eligible
Publisher revision AND the audit/comparability *context*. When the methodology (algorithm, detector,
normalization, metadata revision-distance, evaluation, or report version) changes, the fingerprint
changes, so the same revision becomes eligible again under the new context (a changed-comparability
re-audit) rather than being suppressed.

The ledger is operational state, not a benchmark projection: processed markers are reconstructable
from the report index, but the failed-attempt records are the durable operational log. Read-modify-
write with read-back verification; single-writer (the agent) assumed. This module writes only to
``edenseek-scout`` and never to the Publisher repository.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger
import scout_report_publisher as srp

REVISION_LEDGER_VERSION = "v1"
LEDGER_ARTIFACT = "processed_revisions"   # {issue}/ledger/processed_revisions.json

STATUS_PROCESSED = "processed"
STATUS_FAILED = "failed"


class ScoutRevisionLedgerError(Exception):
    """Raised when the ledger target is unconfigured or a ledger read/write fails."""


def context_fingerprint(versions):
    """Deterministic fingerprint of the static methodology versions (pure). Two runs share a
    fingerprint iff every methodology version matches; a bump changes it — a changed-comparability
    context — so the revision becomes eligible again rather than suppressed."""
    basis = "|".join(f"{k}={versions[k]}" for k in sorted(versions))
    return "fp_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


def entry_key(published_revision_id, fingerprint):
    return f"{published_revision_id}@{fingerprint}"


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ctx(client, context=None):
    if context is not None:
        bucket, issue_prefix, region = context.scout_bucket, context.scout_prefix, context.scout_region
    else:
        bucket = os.getenv(srp.BUCKET_ENV)
        prefix = os.getenv(srp.PREFIX_ENV)
        if not bucket or not prefix:
            raise ScoutRevisionLedgerError(
                f"Scout Repository target is not configured: set {srp.BUCKET_ENV} and {srp.PREFIX_ENV}.")
        issue_prefix, _issue_id = srp._require_issue_prefix(prefix)
        region = os.getenv(srp.REGION_ENV, srp.DEFAULT_REGION)
    client = client or srp._s3_client(region)
    key = f"{issue_prefix}/ledger/{LEDGER_ARTIFACT}.json"
    return client, bucket, issue_prefix, key


def _empty(issue_prefix):
    return {"revision_ledger_version": REVISION_LEDGER_VERSION, "issue_prefix": issue_prefix,
            "updated_at": None, "count": 0, "entries": {}}


def load_ledger(client=None, context=None):
    """Read the current ledger (read-only). Empty ledger when none exists yet."""
    client, bucket, issue_prefix, key = _ctx(client, context)
    try:
        body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
            return _empty(issue_prefix)
        raise ScoutRevisionLedgerError(f"Unable to read ledger s3://{bucket}/{key}: {e}") from e
    except BotoCoreError as e:
        raise ScoutRevisionLedgerError(f"Unable to read ledger s3://{bucket}/{key}: {e}") from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ScoutRevisionLedgerError(f"Ledger is not valid JSON (s3://{bucket}/{key}): {e}") from e


def get_entry(ledger, published_revision_id, fingerprint):
    return (ledger.get("entries") or {}).get(entry_key(published_revision_id, fingerprint))


def is_processed(ledger, published_revision_id, fingerprint):
    """True iff this revision has already been successfully audited-and-persisted under this context."""
    e = get_entry(ledger, published_revision_id, fingerprint)
    return bool(e and e.get("status") == STATUS_PROCESSED)


def _write(client, bucket, key, ledger, issue_prefix):
    ledger["issue_prefix"] = issue_prefix
    ledger["updated_at"] = _now()
    ledger["count"] = len(ledger.get("entries") or {})
    body = srp._dumps(ledger)
    srp._put(client, bucket, key, body, "application/json")
    srp._verify_readback(client, bucket, key, body)
    return ledger


def _upsert(client, published_revision_id, fingerprint, changes, context=None):
    client, bucket, issue_prefix, key = _ctx(client, context)
    ledger = load_ledger(client, context=context)
    entries = ledger.setdefault("entries", {})
    k = entry_key(published_revision_id, fingerprint)
    existing = entries.get(k) or {}
    entry = {
        "revision_id": published_revision_id,
        "context_fingerprint": fingerprint,
        "first_seen": existing.get("first_seen") or _now(),
        "attempts": (existing.get("attempts") or 0) + 1,
        **{f: existing.get(f) for f in ("run_id", "run_seq", "report_id", "completed_at",
                                        "generated_snapshot_revision_id", "comparability",
                                        "failure_stage", "error_codes")},
        **changes,
        "updated_at": _now(),
    }
    entries[k] = entry
    _write(client, bucket, key, ledger, issue_prefix)
    return entry


def mark_processed(published_revision_id, fingerprint, *, run_id, run_seq, report_id, completed_at,
                   generated_snapshot_revision_id, comparability, trigger, client=None, context=None):
    """Record a revision as successfully processed — ONLY after all verified persistence steps.
    Clears any prior failure fields for this key."""
    entry = _upsert(client, published_revision_id, fingerprint, {
        "status": STATUS_PROCESSED, "run_id": run_id, "run_seq": run_seq, "report_id": report_id,
        "completed_at": completed_at, "generated_snapshot_revision_id": generated_snapshot_revision_id,
        "comparability": comparability, "trigger": trigger,
        "failure_stage": None, "error_codes": [],
    }, context=context)
    logger.info("Ledger: revision %s marked processed (run_seq %s, fingerprint %s)",
                published_revision_id, run_seq, fingerprint)
    return entry


def mark_failed(published_revision_id, fingerprint, *, stage, error_codes, trigger,
                run_id=None, client=None, context=None):
    """Record a failed/incomplete run. Never marks the revision processed."""
    entry = _upsert(client, published_revision_id, fingerprint, {
        "status": STATUS_FAILED, "failure_stage": stage, "error_codes": list(error_codes or []),
        "trigger": trigger, **({"run_id": run_id} if run_id else {}),
    }, context=context)
    logger.warning("Ledger: revision %s marked FAILED at stage=%s codes=%s",
                   published_revision_id, stage, error_codes)
    return entry


def unprocessed_eligible(ledger, published_revision_id, fingerprint):
    """Reconciliation helper: True when the current revision is eligible but not yet processed under
    the current context (never audited, or the last attempt failed)."""
    return not is_processed(ledger, published_revision_id, fingerprint)
