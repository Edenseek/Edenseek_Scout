"""Deterministic Historical Intelligence (Phase 4).

Pure analysis over the accumulated ``audit_history`` snapshots — no canonical
dataset is opened, no I/O beyond the in-memory history, no network, no LLM. It
**explains change; it never predicts it.** Diagnostic and observational only: it
does not predict, prescribe, recommend, modify data/scoring, or self-modify
(Charter §4). Identical history → identical output (deterministic replay).
"""
from audit_failure_analysis import FAILURE_DEFS, DOMAIN_CATEGORY

# A change within ±1 percentage point / point is "stable" (approved threshold).
STABLE_EPSILON = 1

DOMAIN_BY_TYPE = {d["failure_type"]: d["domain"] for d in FAILURE_DEFS}

# Inferred publisher-action proxies from reductions in failure counts (observational).
_ACTION_BY_FAILURE = {
    "unreviewed": "reviews_performed",
    "not_approved": "approvals_performed",
    "not_locked": "locks_performed",
    "missing_characters": "characters_added",
    "missing_dialogue": "dialogue_added",
    "missing_metadata": "metadata_completed",
    "unpaged": "page_links_added",
    "status_incomplete": "enrichment_completed",
}

# (name, better_when, accessor) — higher-is-better scores vs lower-is-better volume.
_METRICS = [
    ("quality_score", "higher", lambda s: s.get("quality_score", 0)),
    ("metadata_completeness", "higher", lambda s: s.get("scores", {}).get("metadata_completeness", 0)),
    ("character_consistency", "higher", lambda s: s.get("scores", {}).get("character_consistency", 0)),
    ("dialogue_completeness", "higher", lambda s: s.get("scores", {}).get("dialogue_completeness", 0)),
    ("retrieval_readiness", "higher", lambda s: s.get("scores", {}).get("retrieval_readiness", 0)),
    ("weak_percent", "lower", lambda s: _pct(s.get("weak_total_flagged", 0), s.get("artifact_count", 0))),
]


def _pct(count, total):
    return round(100 * count / total) if total else 0


def _direction(change, better_when):
    if abs(change) <= STABLE_EPSILON:
        return "stable"
    if better_when == "higher":
        return "improving" if change > 0 else "worsening"
    return "improving" if change < 0 else "worsening"


def _consistency(series):
    deltas = [series[i + 1] - series[i] for i in range(len(series) - 1)]
    if all(d >= 0 for d in deltas) or all(d <= 0 for d in deltas):
        return "monotonic"
    return "mixed"


def _confidence(k):
    if k < 2:
        return "insufficient_history"
    if k == 2:
        return "preliminary"
    return "trend"


def _fpct(snap, ftype):
    return _pct(snap.get("failure_summary", {}).get(ftype, 0), snap.get("artifact_count", 0))


def _present(snap, ftype):
    return snap.get("failure_summary", {}).get(ftype, 0) > 0


def _all_failure_types(snaps):
    types = set()
    for s in snaps:
        types.update(s.get("failure_summary", {}).keys())
    return sorted(types)


def build_historical_intelligence(history, dataset_id=None):
    """Analyze the trajectory of a single dataset across its audit snapshots."""
    if not history:
        return _empty(None, 0, "No audit history recorded yet.")

    target = dataset_id or history[-1].get("dataset_id")
    snaps = [s for s in history if s.get("dataset_id") == target]
    k = len(snaps)
    confidence = _confidence(k)
    window = {"first": snaps[0].get("timestamp") if snaps else None,
              "last": snaps[-1].get("timestamp") if snaps else None}

    if k < 2:
        result = _empty(target, k, "Insufficient history: need at least two audits of this dataset.")
        result["window"] = window
        return result

    # ---- Metric trends (whole window) ----
    metrics = []
    for name, better_when, accessor in _METRICS:
        series = [accessor(s) for s in snaps]
        change = series[-1] - series[0]
        metrics.append({
            "name": name, "better_when": better_when,
            "first": series[0], "last": series[-1], "change": change,
            "direction": _direction(change, better_when),
            "consistency": _consistency(series), "series": series,
        })

    # Failure-based analysis only spans snapshots that actually carry failure data
    # (a missing failure_summary means "no data", never "zero failures").
    fsnaps = [s for s in snaps if "failure_summary" in s]
    failure_trends, new_failures, resolved_failures, stagnant = [], [], [], []
    if len(fsnaps) >= 2:
        for ftype in _all_failure_types(fsnaps):
            first_p, last_p = _fpct(fsnaps[0], ftype), _fpct(fsnaps[-1], ftype)
            change = last_p - first_p
            failure_trends.append({
                "failure_type": ftype, "domain": DOMAIN_BY_TYPE.get(ftype, "unknown"),
                "first_percent": first_p, "last_percent": last_p, "change": change,
                "direction": _direction(change, "lower"),
            })
        failure_trends.sort(key=lambda f: (-f["last_percent"], f["failure_type"]))
        new_failures = [t for t in _all_failure_types(fsnaps)
                        if _present(fsnaps[-1], t) and not _present(fsnaps[0], t)]
        resolved_failures = [t for t in _all_failure_types(fsnaps)
                             if _present(fsnaps[0], t) and not _present(fsnaps[-1], t)]
        stagnant = _stagnant_domains(fsnaps)

    # ---- Delta since previous audit (last two snapshots) ----
    delta = _delta(snaps[-2], snaps[-1])

    # ---- Observed correlations (observational only) ----
    correlations = _correlations(fsnaps)

    return {
        "dataset_id": target,
        "snapshots_analyzed": k,
        "confidence": confidence,
        "window": window,
        "metrics": metrics,
        "failure_trends": failure_trends,
        "new_failures": new_failures,
        "resolved_failures": resolved_failures,
        "stagnant_domains": stagnant,
        "delta": delta,
        "observed_correlations": correlations,
        "note": "Observational only: trends and correlations describe measured change. Scout "
                "does not attribute cause, predict outcomes, or recommend actions.",
    }


def _empty(dataset_id, k, note):
    return {
        "dataset_id": dataset_id, "snapshots_analyzed": k,
        "confidence": _confidence(k), "window": {"first": None, "last": None},
        "metrics": [], "failure_trends": [], "new_failures": [], "resolved_failures": [],
        "stagnant_domains": [], "delta": None, "observed_correlations": [], "note": note,
    }


def _domain_series(snaps, domain):
    types = [t for t, d in DOMAIN_BY_TYPE.items() if d == domain]
    if not types:
        return None
    return [round(sum(_fpct(s, t) for t in types) / len(types)) for s in snaps]


def _stagnant_domains(snaps):
    domains = sorted({d for d in DOMAIN_BY_TYPE.values()})
    out = []
    for domain in domains:
        series = _domain_series(snaps, domain)
        if not series:
            continue
        change = series[-1] - series[0]
        if abs(change) <= STABLE_EPSILON and series[-1] > 0:
            out.append({"domain": domain, "first_percent": series[0],
                        "last_percent": series[-1], "change": change})
    out.sort(key=lambda d: (-d["last_percent"], d["domain"]))
    return out


def _delta(prev, cur):
    metrics = {}
    for name, _better, accessor in _METRICS:
        metrics[name] = accessor(cur) - accessor(prev)
    # Failure deltas only when both audits carry failure data.
    if "failure_summary" in prev and "failure_summary" in cur:
        types = sorted(set(prev["failure_summary"]) | set(cur["failure_summary"]))
        failures = {t: _fpct(cur, t) - _fpct(prev, t) for t in types}
        new = [t for t in types if _present(cur, t) and not _present(prev, t)]
        resolved = [t for t in types if _present(prev, t) and not _present(cur, t)]
    else:
        failures, new, resolved = {}, [], []
    return {
        "from": prev.get("timestamp"), "to": cur.get("timestamp"),
        "metrics": metrics, "failures": failures,
        "new_failures": new, "resolved_failures": resolved,
    }


def _correlations(snaps):
    out = []
    for i in range(len(snaps) - 1):
        prev, cur = snaps[i], snaps[i + 1]
        inferred = {}
        for ftype, action in _ACTION_BY_FAILURE.items():
            reduced = prev.get("failure_summary", {}).get(ftype, 0) - cur.get("failure_summary", {}).get(ftype, 0)
            if reduced > 0:
                inferred[action] = reduced
        if not inferred:
            continue
        out.append({
            "interval": {"from": prev.get("timestamp"), "to": cur.get("timestamp")},
            "quality_change": cur.get("quality_score", 0) - prev.get("quality_score", 0),
            "inferred_changes": inferred,
        })
    return out
