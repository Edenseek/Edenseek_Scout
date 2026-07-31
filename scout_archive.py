"""Reports Archive + server-side search over persisted Scout audit metadata (Increment 5).

Presents one issue's audit history as an archive ordered by completion time (newest first), merging
successful reports (from the rebuildable report index) with failed/incomplete runs (from the durable
processed-revision ledger). Marks the current/latest report, historical reports, failed runs, and
methodology (comparability) boundaries. All filtering is **server-side** over the persisted index +
ledger metadata — the browser passes a query and renders; it never recomputes an audit.

Read-only. Reuses `scout_report_index` (the index projection) and `scout_revision_ledger` (the
operational log); no audit logic is duplicated here.
"""
import re

import scout_report_index as sri
import scout_revision_ledger as ledger

# Metric names searchable via range queries (e.g. `precision<0.80`), and where to read them from a
# report record's flattened metrics. Aliases map friendly names to the stored keys.
_METRIC_ALIASES = {
    "metadata_unchanged_rate": "unchanged_metadata_rate",
    "editorial_intervention": "weighted_editorial_intervention_score",
}
_OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b, "=": lambda a, b: a == b, "==": lambda a, b: a == b}
_RANGE_RE = re.compile(r"^([a-z_][a-z0-9_]*)(<=|>=|==|<|>|=)(-?\d+(?:\.\d+)?)$", re.I)
_KV_RE = re.compile(r"^([a-z_][a-z0-9_]*):(.+)$", re.I)


def _report_record(entry, is_latest):
    """An archive record for a successful report (from an index entry)."""
    metrics_flat = {**(entry.get("metrics") or {}), **(entry.get("metadata_metrics") or {})}
    return {
        "record_kind": "report",
        "status": "processed",
        "is_latest": is_latest,
        "is_historical": not is_latest,
        "report_id": entry.get("report_id"), "run_id": entry.get("run_id"),
        "run_seq": entry.get("run_seq"), "issue_id": entry.get("issue_id"),
        "publisher_id": entry.get("publisher_id"), "series_id": entry.get("series_id"),
        "title_group_id": entry.get("title_group_id"),
        "completed_at": entry.get("completed_at"), "measurement_time": entry.get("measurement_time"),
        "event_time": entry.get("event_time"), "certified_at": entry.get("certified_at"),
        "archived_at": entry.get("completed_at"),
        "worst_severity": entry.get("worst_severity"),
        "metadata_status": entry.get("metadata_status"),
        "finding_counts": entry.get("finding_counts"), "finding_codes": entry.get("finding_codes"),
        "published_revision_id": entry.get("published_revision_id"),
        "generated_snapshot_revision_id": entry.get("generated_snapshot_revision_id"),
        "review_id": entry.get("review_id"),
        "geometry_comparability_key": entry.get("geometry_comparability_key"),
        "metadata_comparability_key": entry.get("metadata_comparability_key"),
        "schema_version": entry.get("schema_version"), "algorithm_version": entry.get("algorithm_version"),
        "evaluation_version": entry.get("evaluation_version"),
        "normalization_version": entry.get("normalization_version"),
        "publisher_commit": entry.get("publisher_commit"), "scout_commit": entry.get("scout_commit"),
        "persisted_key": entry.get("persisted_key"), "report_sha256": entry.get("report_sha256"),
        "metrics": metrics_flat,
        "recommendation_text": " ".join(
            f"{f.get('title', '')} {f.get('detail', '')}" for f in (entry.get("findings") or [])).strip(),
    }


def _failed_record(led_entry):
    """An archive record for a failed/incomplete run (from a ledger entry)."""
    return {
        "record_kind": "failed_run",
        "status": led_entry.get("status"),        # failed
        "is_latest": False, "is_historical": False,
        "run_id": led_entry.get("run_id"), "issue_id": None,
        "published_revision_id": led_entry.get("revision_id"),
        "context_fingerprint": led_entry.get("context_fingerprint"),
        "failure_stage": led_entry.get("failure_stage"), "error_codes": led_entry.get("error_codes"),
        "attempts": led_entry.get("attempts"), "trigger": led_entry.get("trigger"),
        "first_seen": led_entry.get("first_seen"), "updated_at": led_entry.get("updated_at"),
        "archived_at": led_entry.get("updated_at"),
    }


def build_archive(client=None, context=None):
    """The archive for the configured issue: successful reports (index) + failed runs (ledger),
    newest first, with latest/historical/failed marks and methodology boundaries between adjacent
    reports. Read-only."""
    index = sri.load_index(client, context=context)
    entries = index.get("entries", [])            # already newest-first (by run_seq)
    # ``latest`` is canonically a dict ({report_id, run_seq, ...}); tolerate a malformed/absent value
    # (fall back to the newest entry) so the archive never 503s over a bad pointer.
    _latest = index.get("latest")
    latest_run_seq = (_latest.get("run_seq") if isinstance(_latest, dict)
                      else (entries[0].get("run_seq") if entries else None))
    reports = [_report_record(e, e.get("run_seq") == latest_run_seq) for e in entries]

    # methodology boundary: does this report's comparability differ from the next-NEWER report?
    for i, rec in enumerate(reports):
        newer = reports[i - 1] if i > 0 else None
        rec["methodology_boundary"] = {
            "geometry": bool(newer) and newer["geometry_comparability_key"] != rec["geometry_comparability_key"],
            "metadata": bool(newer) and newer["metadata_comparability_key"] != rec["metadata_comparability_key"],
        }

    try:
        led = ledger.load_ledger(client, context=context)
        failed = [_failed_record(e) for e in (led.get("entries") or {}).values()
                  if e.get("status") == ledger.STATUS_FAILED]
    except ledger.ScoutRevisionLedgerError:
        failed = []

    records = reports + failed
    records.sort(key=lambda r: (r.get("archived_at") or "", r.get("run_seq") or 0), reverse=True)
    return {
        "issue_prefix": index.get("issue_prefix"),
        "count": len(records), "report_count": len(reports), "failed_count": len(failed),
        "latest": next((r for r in reports if r["is_latest"]), None),
        "records": records,
    }


# --------------------------------------------------------------------------- #
# Query grammar (server-side)
# --------------------------------------------------------------------------- #
def parse_query(q):
    """Parse a search string into structured filters. Supported tokens:
      metric range   ``precision<0.80``  ``metadata_unchanged_rate>=0.90``
      finding        ``finding:geometry.false_panels``
      severity       ``severity:WARNING``
      field:value    ``publisher:<id>`` ``issue:<id>`` ``prompt_version:v12`` ``schema_version:...``
                     ``algorithm_version:...`` ``model:...`` ``revision:...`` ``commit:...``
                     ``report_id:...`` ``run_id:...`` ``date_from:...`` ``date_to:...`` ``kind:report|failed_run``
      free text      matched against recommendation text.
    Multiple tokens are ANDed.
    """
    ranges, fields, findings, severities, kinds, texts = [], {}, [], [], [], []
    for tok in (q or "").split():
        m = _RANGE_RE.match(tok)
        if m:
            ranges.append((m.group(1).lower(), m.group(2), float(m.group(3))))
            continue
        kv = _KV_RE.match(tok)
        if kv:
            key, val = kv.group(1).lower(), kv.group(2)
            if key == "finding":
                findings.append(val)
            elif key == "severity":
                severities.append(val.upper())
            elif key == "kind":
                kinds.append(val)
            else:
                fields[key] = val
            continue
        texts.append(tok.lower())
    return {"ranges": ranges, "fields": fields, "findings": findings,
            "severities": severities, "kinds": kinds, "texts": texts}


_FIELD_ACCESSORS = {
    "publisher": lambda r: r.get("publisher_id"),
    "issue": lambda r: r.get("issue_id"),
    "series": lambda r: r.get("series_id"),
    "report_id": lambda r: r.get("report_id"),
    "run_id": lambda r: r.get("run_id"),
    "prompt_version": lambda r: None,   # populated once the Publisher emits prompt ids
    "schema_version": lambda r: r.get("schema_version"),
    "algorithm_version": lambda r: r.get("algorithm_version"),
    "evaluation_version": lambda r: r.get("evaluation_version"),
}


def _metric(record, name):
    key = _METRIC_ALIASES.get(name, name)
    return (record.get("metrics") or {}).get(key)


def _matches(record, f):
    for field, val in f["fields"].items():
        if field in ("date_from",):
            if (record.get("archived_at") or "") < val:
                return False
        elif field in ("date_to",):
            if (record.get("archived_at") or "") > val:
                return False
        elif field == "revision":
            if val not in (record.get("published_revision_id"),
                           record.get("generated_snapshot_revision_id"), record.get("review_id")):
                return False
        elif field == "commit":
            if val not in (record.get("publisher_commit") or "") \
                    and val not in (record.get("scout_commit") or ""):
                return False
        else:
            acc = _FIELD_ACCESSORS.get(field)
            if acc is None or acc(record) != val:
                return False
    for kind in f["kinds"]:
        if record.get("record_kind") != kind:
            return False
    for code in f["findings"]:
        if code not in (record.get("finding_codes") or []):
            return False
    for sev in f["severities"]:
        if (record.get("finding_counts") or {}).get(sev, 0) <= 0:
            return False
    for name, op, val in f["ranges"]:
        v = _metric(record, name)
        if v is None or not _OPS[op](v, val):
            return False
    for term in f["texts"]:
        if term not in (record.get("recommendation_text") or "").lower():
            return False
    return True


def search_archive(archive, query):
    """Filter an archive's records by a parsed query (or a raw string). Pure/server-side."""
    f = query if isinstance(query, dict) else parse_query(query)
    hits = [r for r in archive.get("records", []) if _matches(r, f)]
    return {"query": f, "count": len(hits), "records": hits}
