"""Scout Report Index — a rebuildable projection over the immutable persisted delta reports.

The authoritative artifacts are the immutable ``{issue}/history/scout_delta_report_{seq}.json``
reports. This module maintains a per-issue **index** — a searchable, newest-first projection of
those reports at ``{issue}/reports/report_index.json`` (R1 latest-state). The index is *derived*
and fully **rebuildable** from history; the reports remain the source of truth. It carries a
``latest`` pointer to the current completed report and, per entry, the searchable metadata and the
formal comparability axes.

Comparability contract (see docs/architecture/SCOUT_REPORT_INDEX.md): two reports are DIRECTLY
COMPARABLE iff all four axes match — ``report_version`` (report format), ``algorithm_version``
(the delta computation), ``schema_version`` (the Publisher input contract consumed), and
``evaluation_version`` (the findings/severity rules). A change on any axis is a boundary; trend
graphs must segment on ``comparability_key`` and never draw a continuous line across a boundary
without warning. (Upstream Publisher prompt/model changes are not a Scout axis; they surface here
via ``schema_version`` and the generated-snapshot revision id.)

Boundaries: writing the index is the agent's job (in the same transaction as persisting the
report); the UI only READS the index + reports. Rebuild is a maintenance operation. Read-only over
the Publisher repository at all times — this module touches only ``edenseek-scout``.
"""
import hashlib
import json
import os

from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger
import scout_report_publisher as srp

REPORT_INDEX_VERSION = "v1"
INDEX_ARTIFACT = "report_index"  # {issue}/reports/report_index.json (latest-state projection)

# Numeric metrics the index carries for range-search and trend graphs (geometry task family).
METRIC_FIELDS = ("precision", "recall", "split_rate", "merge_rate",
                 "missing_count", "spread_missing_count", "false_count")

# Comparability is per TASK FAMILY: geometry and metadata metrics are only comparable under the
# conditions that actually govern each. The axis VALUES are assembled from a report body; the
# field lists below document the contract.
GEOMETRY_AXES = ("task", "metric_definition_version", "geometry_detector_version",
                 "iou_threshold", "normalization_version")
METADATA_AXES = ("task", "metric_definition_version", "metadata_prompt_version", "metadata_prompt_sha256",
                 "metadata_model", "metadata_schema_version", "metadata_revision_distance_version",
                 "metadata_accuracy_version", "normalization_version", "evaluation_version")


class ScoutReportIndexError(Exception):
    """Raised when the index target is unconfigured or an index read/write fails."""


# --------------------------------------------------------------------------- #
# Comparability contract (per task family)
# --------------------------------------------------------------------------- #
def comparability_key(axes):
    """Deterministic key over an axis dict (order-independent). Equal keys ⇒ directly comparable."""
    basis = "|".join(f"{k}={axes[k]}" for k in sorted(axes))
    return "cmp_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


def geometry_axes(body):
    """The conditions a valid geometry-benchmark comparison requires."""
    prov = body.get("provenance", {}) or {}
    det = prov.get("geometry_detector", {}) or {}
    return {
        "task": "geometry",
        "metric_definition_version": body.get("algorithm_version"),
        "geometry_detector_version": det.get("match_version"),
        "iou_threshold": det.get("iou_threshold"),
        "normalization_version": prov.get("normalization_version"),
    }


def metadata_axes(body):
    """The conditions a valid metadata comparison requires (prompt/model/schema/eval + normalization)."""
    prov = body.get("provenance", {}) or {}
    mp = prov.get("metadata_provenance", {}) or {}
    return {
        "task": "metadata",
        "metric_definition_version": body.get("algorithm_version"),
        "metadata_prompt_version": mp.get("prompt_version"),
        # prompt_sha256 hashes the prompt templates: a silent (un-versioned) prompt edit changes the
        # sha even when the human-label prompt_version is unchanged, forcing a methodology boundary
        # rather than silently contaminating a comparability series.
        "metadata_prompt_sha256": mp.get("prompt_sha256"),
        "metadata_model": mp.get("model"),
        "metadata_schema_version": f"{mp.get('generated_schema_version')}/{mp.get('approved_schema_version')}",
        "metadata_revision_distance_version": prov.get("metadata_revision_distance_version"),
        "metadata_accuracy_version": (body.get("metadata_metrics") or {}).get("metadata_accuracy_version"),
        "normalization_version": prov.get("normalization_version"),
        "evaluation_version": body.get("evaluation_version"),
    }


def build_comparability(body):
    """Both task-family comparability keys + the axis values that produced them. Reports with equal
    per-task keys may form one continuous benchmark series for that task; different keys stay visible
    but must be separated by a methodology boundary and never silently combined."""
    ga, ma = geometry_axes(body), metadata_axes(body)
    return {"geometry": comparability_key(ga), "metadata": comparability_key(ma),
            "geometry_axes": ga, "metadata_axes": ma}


def comparability_diff(axes_a, axes_b):
    """The axes on which two axis dicts differ (empty ⇒ directly comparable)."""
    return sorted(k for k in set(axes_a) | set(axes_b) if axes_a.get(k) != axes_b.get(k))


# --------------------------------------------------------------------------- #
# Projection: persisted report envelope -> index entry
# --------------------------------------------------------------------------- #
def build_index_entry(envelope):
    """Project one persisted delta-report envelope into a searchable index entry (pure).

    Everything the archive/search/graph layer needs without opening the full report; the full
    report stays addressable via ``persisted_key``.
    """
    prov = envelope.get("provenance", {}) or {}
    ident = envelope.get("issue_identity", {}) or {}
    comparability = envelope.get("comparability") or build_comparability(envelope)
    return {
        "report_id": envelope.get("report_id"),
        "run_id": envelope.get("run_id"),
        "run_seq": envelope.get("run_seq"),
        "completed_at": envelope.get("completed_at"),          # measurement time
        "measurement_time": envelope.get("completed_at"),
        "event_time": envelope.get("event_time"),              # Publisher publication time
        "certified_at": envelope.get("certified_at"),          # Platform certification time
        "publisher_id": ident.get("publisher_id"),
        "title_group_id": ident.get("title_group_id"),
        "series_id": ident.get("series_id"),
        "issue_id": envelope.get("issue_id") or ident.get("issue_id"),
        "published_revision_id": prov.get("published_revision_id"),
        "generated_snapshot_revision_id": prov.get("generated_snapshot_revision_id"),
        "review_id": prov.get("review_id"),
        "applicability": envelope.get("applicability"),
        "metrics": dict(envelope.get("metrics", {}) or {}),
        "geometry_benchmark": dict((envelope.get("geometry_benchmark") or {})),
        "metadata_benchmark": dict((envelope.get("metadata_benchmark") or {})),
        "metadata_metrics": dict((envelope.get("metadata_metrics") or {})),
        "metadata_status": envelope.get("metadata_status"),
        "compared_artifacts": envelope.get("compared_artifacts"),
        "finding_counts": dict(envelope.get("finding_counts", {}) or {}),
        "finding_codes": list(envelope.get("finding_codes", []) or []),
        "findings": [{k: f.get(k) for k in ("code", "severity", "title", "detail")}
                     for f in (envelope.get("findings") or [])],
        "worst_severity": envelope.get("worst_severity"),
        # comparability axes (per task family, so a graph can explain a boundary)
        "report_version": envelope.get("report_version"),
        "algorithm_version": envelope.get("algorithm_version"),
        "schema_version": envelope.get("schema_version"),
        "evaluation_version": envelope.get("evaluation_version"),
        "normalization_version": (prov.get("normalization_version")),
        "schema_versions": dict(envelope.get("schema_versions", {}) or {}),
        "comparability": comparability,
        "geometry_comparability_key": comparability["geometry"],
        "metadata_comparability_key": comparability["metadata"],
        "publisher_commit": envelope.get("publisher_commit"),
        "scout_commit": envelope.get("scout_commit"),
        "persisted_key": dict(envelope.get("persisted_key", {}) or {}),
        "report_sha256": envelope.get("report_sha256"),
    }


def _empty_index(issue_prefix):
    return {"report_index_version": REPORT_INDEX_VERSION, "issue_prefix": issue_prefix,
            "generated_at": None, "latest": None, "count": 0, "entries": []}


def _finalize(index, issue_prefix):
    """Sort entries newest-first, set the latest pointer and count (pure)."""
    entries = sorted(index.get("entries", []), key=lambda e: (e.get("run_seq") or 0), reverse=True)
    latest = entries[0] if entries else None
    index["entries"] = entries
    index["count"] = len(entries)
    index["issue_prefix"] = issue_prefix
    index["report_index_version"] = REPORT_INDEX_VERSION
    index["generated_at"] = latest.get("completed_at") if latest else None
    index["latest"] = ({"report_id": latest["report_id"], "run_seq": latest["run_seq"],
                        "persisted_key": latest.get("persisted_key")} if latest else None)
    return index


# --------------------------------------------------------------------------- #
# S3 read/write for the index object (edenseek-scout only)
# --------------------------------------------------------------------------- #
def _index_context(client, context=None):
    if context is not None:
        bucket, issue_prefix, region = context.scout_bucket, context.scout_prefix, context.scout_region
    else:
        bucket = os.getenv(srp.BUCKET_ENV)
        prefix = os.getenv(srp.PREFIX_ENV)
        if not bucket or not prefix:
            raise ScoutReportIndexError(
                f"Scout Repository target is not configured: set {srp.BUCKET_ENV} and {srp.PREFIX_ENV}.")
        issue_prefix, _issue_id = srp._require_issue_prefix(prefix)
        region = os.getenv(srp.REGION_ENV, srp.DEFAULT_REGION)
    client = client or srp._s3_client(region)
    key = f"{issue_prefix}/reports/{INDEX_ARTIFACT}.json"
    return client, bucket, issue_prefix, key


def load_index(client=None, context=None):
    """Read the current report index (read-only). Returns an empty index when none exists yet."""
    client, bucket, issue_prefix, key = _index_context(client, context)
    try:
        body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
            return _empty_index(issue_prefix)
        raise ScoutReportIndexError(f"Unable to read report index s3://{bucket}/{key}: {e}") from e
    except BotoCoreError as e:
        raise ScoutReportIndexError(f"Unable to read report index s3://{bucket}/{key}: {e}") from e
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise ScoutReportIndexError(f"Report index is not valid JSON (s3://{bucket}/{key}): {e}") from e


def _write_index(client, bucket, key, index):
    body = srp._dumps(index)
    srp._put(client, bucket, key, body, "application/json")
    srp._verify_readback(client, bucket, key, body)
    return body


def update_index(entry, client=None, context=None):
    """Insert (or replace by run_seq) one entry and rewrite the index, verified. Called by the agent
    runner immediately after a report is persisted+verified — the second half of the transaction."""
    client, bucket, issue_prefix, key = _index_context(client, context)
    index = load_index(client, context=context)
    entries = [e for e in index.get("entries", []) if e.get("run_seq") != entry.get("run_seq")]
    entries.append(entry)
    index["entries"] = entries
    _finalize(index, issue_prefix)
    _write_index(client, bucket, key, index)
    logger.info("Report index updated: run_seq=%s count=%d latest=%s",
                entry.get("run_seq"), index["count"], index["latest"]["report_id"])
    return index


def rebuild_index(client=None, context=None):
    """Rebuild the index from scratch by scanning the immutable history reports — proof that the
    index is a derived projection, and the reconciliation path if it is ever lost or divergent."""
    client, bucket, issue_prefix, key = _index_context(client, context)
    keys = srp.list_history_keys(client, srp.SCOUT_DELTA_REPORT_TYPE, context=context)
    entries = []
    for hk in keys:
        try:
            envelope = json.loads(srp.read_object(client, hk, context=context))
        except (json.JSONDecodeError, srp.ScoutReportPublishError) as e:
            logger.warning("Skipping unreadable history report %s during rebuild: %s", hk, e)
            continue
        entries.append(build_index_entry(envelope))
    index = _finalize({"entries": entries}, issue_prefix)
    _write_index(client, bucket, key, index)
    logger.info("Report index rebuilt from %d history report(s)", len(entries))
    return index


# --------------------------------------------------------------------------- #
# Read model: pure query + metric-series projection (server-side; UI never filters)
# --------------------------------------------------------------------------- #
def _in_range(value, lo, hi):
    if value is None:
        return False
    if lo is not None and value < lo:
        return False
    if hi is not None and value > hi:
        return False
    return True


def query_index(index, filters=None):
    """Filter index entries (pure, server-side). Recognized filters: ``report_id``, ``issue_id``,
    ``publisher_id``, ``series_id``, ``title_group_id``, ``revision`` (matches approved or generated
    revision), ``finding_code``, ``severity`` (entry has ≥1 finding of that severity),
    ``schema_version``, ``commit`` (publisher or scout, substring), ``date_from`` / ``date_to``
    (ISO ``completed_at``), ``comparability_key``, and per-metric ``<metric>_min`` / ``<metric>_max``.
    """
    f = filters or {}
    out = []
    for e in index.get("entries", []):
        if f.get("report_id") and e.get("report_id") != f["report_id"]:
            continue
        if f.get("run_id") and e.get("run_id") != f["run_id"]:
            continue
        for field in ("issue_id", "publisher_id", "series_id", "title_group_id",
                      "geometry_comparability_key", "metadata_comparability_key", "schema_version"):
            if f.get(field) and e.get(field) != f[field]:
                break
        else:
            rev = f.get("revision")
            if rev and rev not in (e.get("published_revision_id"), e.get("generated_snapshot_revision_id")):
                continue
            if f.get("finding_code") and f["finding_code"] not in (e.get("finding_codes") or []):
                continue
            if f.get("severity") and (e.get("finding_counts", {}) or {}).get(f["severity"], 0) <= 0:
                continue
            commit = f.get("commit")
            if commit and commit not in (e.get("publisher_commit") or "") \
                    and commit not in (e.get("scout_commit") or ""):
                continue
            if f.get("date_from") and (e.get("completed_at") or "") < f["date_from"]:
                continue
            if f.get("date_to") and (e.get("completed_at") or "") > f["date_to"]:
                continue
            metrics = e.get("metrics", {}) or {}
            ok = True
            for m in METRIC_FIELDS:
                if (f.get(f"{m}_min") is not None or f.get(f"{m}_max") is not None) and \
                        not _in_range(metrics.get(m), f.get(f"{m}_min"), f.get(f"{m}_max")):
                    ok = False
                    break
            if ok:
                out.append(e)
    return out


def metric_series(index, metrics=None, task="geometry"):
    """Project the index into per-metric time series (oldest→newest) with comparability segments.

    Metrics are segmented by the ``task``-family comparability key (``geometry`` or ``metadata``):
    a graph draws a continuous line only within a segment, and marks ``boundaries`` (run_seqs where
    the key changed) so metrics produced under different detectors/thresholds/prompts/models/schemas
    are never silently joined into one improvement claim.
    """
    metrics = metrics or list(METRIC_FIELDS)
    key_field = "metadata_comparability_key" if task == "metadata" else "geometry_comparability_key"
    ordered = sorted(index.get("entries", []), key=lambda e: (e.get("run_seq") or 0))
    series = {}
    for m in metrics:
        points, segments, boundaries, prev_key = [], [], [], None
        for e in ordered:
            key = e.get(key_field)
            pt = {"run_seq": e.get("run_seq"), "completed_at": e.get("completed_at"),
                  "value": (e.get("metrics", {}) or {}).get(m), "comparability_key": key}
            points.append(pt)
            if key != prev_key:
                if prev_key is not None:
                    boundaries.append(e.get("run_seq"))
                segments.append({"comparability_key": key, "run_seqs": []})
                prev_key = key
            segments[-1]["run_seqs"].append(e.get("run_seq"))
        series[m] = {"task": task, "points": points, "segments": segments, "boundaries": boundaries}
    return series
