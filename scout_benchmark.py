"""Weighted benchmark projections across the Scout hierarchy (reporting Increment 3).

Builds issue → series → publisher → platform benchmark projections from the per-issue report
indexes (themselves rebuildable projections over the immutable reports). Four invariants are
structural, not optional:

1. **Weighted from counts, never averaging percentages.** Every metric aggregates by summing the
   underlying numerators and denominators, then dividing — `sum(numerator) / sum(denominator)`.
2. **Sample size on every point and segment.** Each carries `sample_sizes` (reports + domain
   denominators: pages/panels for geometry, fields/artifacts for metadata) alongside the value.
3. **Explicit methodology boundaries.** Metrics are segmented per task by `comparability_key`;
   `series()` marks boundaries with the axes that changed, so a methodology shift is never read as a
   model improvement, and incompatible segments are never combined into one aggregate.
4. **Dual time.** Every point carries both `event_time` (Publisher publication) and
   `measurement_time` (Scout), and `series()` can order by either — so delayed reprocessing,
   methodology migrations, and backfilled publications don't distort a time series.

Failed/incomplete runs never reach here (they live only in the ledger, not the report index), so
benchmarks are computed over successful runs only. Read-only over the report indexes; writes only to
`edenseek-scout`. Fully rebuildable from the immutable reports.
"""
import json
import os

from botocore.exceptions import BotoCoreError, ClientError

from logging_config import logger
import scout_report_publisher as srp
import scout_report_index as sri

BENCHMARK_PROJECTION_VERSION = "v1"

# metric -> how to read (numerator, denominator) from an index entry's task benchmark block.
# ("ratios", name)  -> geometry_benchmark["ratios"][name] = {numerator, denominator}
# ("pair", (n, d))  -> geometry_benchmark[n] / geometry_benchmark[d]
GEOMETRY_METRICS = {
    "precision": ("ratios", "precision"),
    "recall": ("ratios", "recall"),
    "split_rate": ("ratios", "split_rate"),
    "merge_rate": ("ratios", "merge_rate"),
    "false_rate": ("ratios", "false_rate"),
    "missing_rate": ("ratios", "missing_rate"),
    "unchanged_geometry_rate": ("ratios", "unchanged_geometry_rate"),
    "corrections_per_page": ("pair", ("total_human_geometry_corrections", "pages_evaluated")),
}
# ("field", name) -> metadata_benchmark[name] = {numerator, denominator}
# ("pair", (n, d)) -> metadata_benchmark[n] / metadata_benchmark[d]
METADATA_METRICS = {
    "accepted_unchanged_rate": ("field", "accepted_unchanged_rate"),
    "minor_wording_edit_rate": ("field", "minor_wording_edit_rate"),
    "moderate_rewrite_rate": ("field", "moderate_rewrite_rate"),
    "major_rewrite_rate": ("field", "major_rewrite_rate"),
    "complete_replacement_rate": ("field", "complete_replacement_rate"),
    "corrections_per_artifact": ("field", "corrections_per_artifact"),
    "weighted_editorial_intervention_score": ("field", "weighted_editorial_intervention_score"),
    "average_revision_distance": ("pair", ("revision_distance_sum", "comparable_fields")),
}
_TASKS = {
    "geometry": {"metrics": GEOMETRY_METRICS, "block": "geometry_benchmark",
                 "key": "geometry_comparability_key", "axes": "geometry_axes",
                 "sizes": {"generated_panels": "generated_panels_evaluated",
                           "approved_panels": "approved_panels_evaluated", "pages": "pages_evaluated"}},
    "metadata": {"metrics": METADATA_METRICS, "block": "metadata_benchmark",
                 "key": "metadata_comparability_key", "axes": "metadata_axes",
                 "sizes": {"comparable_fields": "comparable_fields", "artifacts": "comparable_artifacts"}},
}


class ScoutBenchmarkError(Exception):
    """Raised when the benchmark target is unconfigured or a projection read/write fails."""


def _num_den(block, spec):
    kind, ref = spec
    if kind == "ratios":
        r = (block.get("ratios") or {}).get(ref)
        return (r.get("numerator"), r.get("denominator")) if r else None
    if kind == "field":
        r = block.get(ref)
        return (r.get("numerator"), r.get("denominator")) if isinstance(r, dict) else None
    if kind == "pair":
        n, d = ref
        if n in block and d in block:
            return (block.get(n), block.get(d))
    return None


def _entry_point(entry, task):
    """One benchmark point for an entry+task, or None if that task isn't measured in this report."""
    cfg = _TASKS[task]
    block = entry.get(cfg["block"]) or {}
    if not block or (task == "metadata" and not block.get("applicable")):
        return None
    if task == "metadata" and not block.get("comparable_fields"):
        return None                                # abstained report — not a metadata measurement
    metrics = {}
    for name, spec in cfg["metrics"].items():
        nd = _num_den(block, spec)
        if nd is None or nd[0] is None or nd[1] is None:
            continue
        num, den = nd
        metrics[name] = {"value": round(num / den, 6) if den else None,
                         "numerator": num, "denominator": den}
    if not metrics:
        return None
    sizes = {"reports": 1}
    for out, src in cfg["sizes"].items():
        sizes[out] = block.get(src)
    return {
        "run_seq": entry.get("run_seq"), "report_id": entry.get("report_id"),
        "issue_id": entry.get("issue_id"),
        "event_time": entry.get("event_time"), "measurement_time": entry.get("measurement_time"),
        "certified_at": entry.get("certified_at"),
        "comparability_key": entry.get(cfg["key"]),
        "metrics": metrics, "sample_sizes": sizes,
    }


def _aggregate_segment(points, task, comparability_key, axes):
    """Weighted aggregate over a segment's points: sum numerators + denominators, then divide."""
    cfg = _TASKS[task]
    metric_names = set()
    for p in points:
        metric_names.update(p["metrics"])
    metrics = {}
    for name in sorted(metric_names):
        num = sum(p["metrics"][name]["numerator"] for p in points if name in p["metrics"])
        den = sum(p["metrics"][name]["denominator"] for p in points if name in p["metrics"])
        metrics[name] = {"numerator": num, "denominator": den,
                         "rate": round(num / den, 6) if den else None}
    sizes = {"reports": len(points)}
    for out in cfg["sizes"]:
        sizes[out] = sum((p["sample_sizes"].get(out) or 0) for p in points)
    return {"comparability_key": comparability_key, "axes": axes,
            "sample_sizes": sizes, "metrics": metrics}


def build_projection(entries, scope, generated_at):
    """Build one scope's benchmark projection (pure). ``entries`` are index entries (successful runs);
    ``scope`` = {level, publisher_id?, series_id?, issue_id?}. Aggregates per task, per comparability
    segment, from counts — with sample sizes and both timestamps on every point."""
    entries = sorted(entries, key=lambda e: (e.get("run_seq") or 0))
    projection = {
        "benchmark_projection_version": BENCHMARK_PROJECTION_VERSION,
        "scope": scope,
        "measurement_generated_at": generated_at,
        "sample_sizes": {
            "reports": len(entries),
            "issues": len({e.get("issue_id") for e in entries}),
            "series": len({(e.get("publisher_id"), e.get("series_id")) for e in entries}),
            "publishers": len({e.get("publisher_id") for e in entries}),
        },
    }
    for task, cfg in _TASKS.items():
        axes_by_key = {}
        points = []
        for e in entries:
            pt = _entry_point(e, task)
            if pt is None:
                continue
            points.append(pt)
            axes_by_key.setdefault(pt["comparability_key"], (e.get("comparability") or {}).get(cfg["axes"]))
        segments = {}
        for key in sorted(k for k in axes_by_key if k is not None):
            seg_pts = [p for p in points if p["comparability_key"] == key]
            segments[key] = _aggregate_segment(seg_pts, task, key, axes_by_key[key])
        projection[task] = {"segments": segments, "points": points}
    return projection


def series(projection, task, metric, order_by="measurement_time"):
    """Ordered time series for one metric, segmented by comparability (pure). Supports either time
    axis (``event_time`` | ``measurement_time``). Draws continuous only within a segment; ``boundaries``
    marks positions where the methodology changed, with the axes that differ."""
    if order_by not in ("event_time", "measurement_time"):
        raise ScoutBenchmarkError(f"order_by must be event_time or measurement_time, got {order_by!r}")
    pts = projection.get(task, {}).get("points", [])
    segs = projection.get(task, {}).get("segments", {})
    ordered = sorted(pts, key=lambda p: (p.get(order_by) or "", p.get("run_seq") or 0))
    out_points, boundaries, prev_key = [], [], None
    for p in ordered:
        key = p["comparability_key"]
        m = p["metrics"].get(metric)
        out_points.append({
            "run_seq": p["run_seq"], "report_id": p["report_id"], "issue_id": p["issue_id"],
            "event_time": p["event_time"], "measurement_time": p["measurement_time"],
            "value": (m or {}).get("value"), "numerator": (m or {}).get("numerator"),
            "denominator": (m or {}).get("denominator"),
            "sample_sizes": p["sample_sizes"], "comparability_key": key,
        })
        if key != prev_key:
            if prev_key is not None:
                boundaries.append({"at_run_seq": p["run_seq"], "from": prev_key, "to": key,
                                   "changed_axes": _axes_diff(segs.get(prev_key), segs.get(key))})
            prev_key = key
    return {"task": task, "metric": metric, "order_by": order_by,
            "points": out_points, "boundaries": boundaries}


def _axes_diff(seg_a, seg_b):
    a = (seg_a or {}).get("axes") or {}
    b = (seg_b or {}).get("axes") or {}
    return {k: {"from": a.get(k), "to": b.get(k)}
            for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


# --------------------------------------------------------------------------- #
# Hierarchy build over the scout repository (rebuildable from immutable reports)
# --------------------------------------------------------------------------- #
def _roots(issue_prefix):
    """Parse (publisher_root, series_root, ids) from a full issue ownership-chain prefix."""
    segs = issue_prefix.strip("/").split("/")
    idx = {name: i for i, name in enumerate(segs)}
    pub = segs[idx["publishers"] + 1]
    series = segs[idx["series"] + 1]
    tg = segs[idx["title_groups"] + 1]
    issue = segs[idx["issues"] + 1]
    return {
        "publisher_id": pub, "title_group_id": tg, "series_id": series, "issue_id": issue,
        "publisher_root": f"publishers/{pub}",
        "series_root": f"publishers/{pub}/title_groups/{tg}/series/{series}",
        "issue_prefix": issue_prefix,
    }


def discover_issue_indexes(client, bucket):
    """List every per-issue report index in the scout bucket, returning (issue_prefix, index)."""
    out, continuation = [], None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": "publishers/"}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        try:
            resp = client.list_objects_v2(**kwargs)
        except (ClientError, BotoCoreError) as e:
            raise ScoutBenchmarkError(f"Unable to enumerate report indexes: {e}") from e
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.endswith(f"/reports/{sri.INDEX_ARTIFACT}.json"):
                issue_prefix = key[: -len(f"/reports/{sri.INDEX_ARTIFACT}.json")]
                try:
                    idx = json.loads(client.get_object(Bucket=bucket, Key=key)["Body"].read())
                except (ClientError, BotoCoreError, json.JSONDecodeError) as e:
                    logger.warning("Skipping unreadable index %s: %s", key, e)
                    continue
                out.append((issue_prefix, idx))
        if resp.get("IsTruncated"):
            continuation = resp.get("NextContinuationToken")
        else:
            break
    return out


def _persist(client, bucket, key, projection):
    body = srp._dumps(projection)
    srp._put(client, bucket, key, body, "application/json")
    srp._verify_readback(client, bucket, key, body)
    return key


def rebuild_all(client=None, generated_at="1970-01-01T00:00:00Z", context=None):
    """Rebuild + persist every benchmark projection (issue/series/publisher/platform) from the report
    indexes. Rebuildable + idempotent. Returns the keys written per level."""
    if context is not None:
        bucket = context.scout_bucket
        region = context.scout_region
    else:
        bucket = os.getenv(srp.BUCKET_ENV)
        if not bucket:
            raise ScoutBenchmarkError(f"Scout Repository bucket not configured: set {srp.BUCKET_ENV}.")
        region = os.getenv(srp.REGION_ENV, srp.DEFAULT_REGION)
    client = client or srp._s3_client(region)

    discovered = discover_issue_indexes(client, bucket)
    issue_entries, series_entries, publisher_entries, platform_entries = {}, {}, {}, []
    issue_scope, series_scope, publisher_scope = {}, {}, {}
    for issue_prefix, idx in discovered:
        r = _roots(issue_prefix)
        entries = idx.get("entries", [])
        issue_entries.setdefault(issue_prefix, []).extend(entries)
        series_entries.setdefault(r["series_root"], []).extend(entries)
        publisher_entries.setdefault(r["publisher_root"], []).extend(entries)
        platform_entries.extend(entries)
        issue_scope[issue_prefix] = {"level": "issue", **{k: r[k] for k in
                                     ("publisher_id", "title_group_id", "series_id", "issue_id")}}
        series_scope[r["series_root"]] = {"level": "series", "publisher_id": r["publisher_id"],
                                          "title_group_id": r["title_group_id"], "series_id": r["series_id"]}
        publisher_scope[r["publisher_root"]] = {"level": "publisher", "publisher_id": r["publisher_id"]}

    written = {"issue": [], "series": [], "publisher": [], "platform": None}
    for prefix, entries in issue_entries.items():
        proj = build_projection(entries, issue_scope[prefix], generated_at)
        written["issue"].append(_persist(client, bucket, f"{prefix}/benchmark/benchmark.json", proj))
    for root, entries in series_entries.items():
        proj = build_projection(entries, series_scope[root], generated_at)
        written["series"].append(_persist(client, bucket, f"{root}/benchmark/benchmark.json", proj))
    for root, entries in publisher_entries.items():
        proj = build_projection(entries, publisher_scope[root], generated_at)
        written["publisher"].append(_persist(client, bucket, f"{root}/benchmark/benchmark.json", proj))
    platform = build_projection(platform_entries, {"level": "platform"}, generated_at)
    written["platform"] = _persist(client, bucket, "benchmark/platform.json", platform)

    logger.info("Benchmark projections rebuilt: %d issue, %d series, %d publisher, 1 platform",
                len(written["issue"]), len(written["series"]), len(written["publisher"]))
    return written


def load_projection(key, client=None, context=None):
    """Read a persisted benchmark projection by key (read-only). None if absent."""
    if context is not None:
        bucket = context.scout_bucket
        region = context.scout_region
    else:
        bucket = os.getenv(srp.BUCKET_ENV)
        if not bucket:
            raise ScoutBenchmarkError(f"Scout Repository bucket not configured: set {srp.BUCKET_ENV}.")
        region = os.getenv(srp.REGION_ENV, srp.DEFAULT_REGION)
    client = client or srp._s3_client(region)
    try:
        return json.loads(client.get_object(Bucket=bucket, Key=key)["Body"].read())
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
            return None
        raise ScoutBenchmarkError(f"Unable to read projection s3://{bucket}/{key}: {e}") from e
    except (BotoCoreError, json.JSONDecodeError) as e:
        raise ScoutBenchmarkError(f"Unable to read projection s3://{bucket}/{key}: {e}") from e
