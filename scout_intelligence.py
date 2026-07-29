"""Machine-readable Geometry & Metadata Intelligence projections (reporting Increment 4).

Geometry Intelligence and Metadata Intelligence are first-class, read-only consumers of the SAME
persisted Scout contracts the dashboard uses — the report index, the immutable reports, and the
benchmark projections — never HTML scrapers. Each receives ONLY its domain-relevant projection plus
provenance and comparability metadata, versioned by its contract.

Geometry Intelligence surfaces recurring panel failure modes and version-correlated improvements.
Metadata Intelligence surfaces weak fields, common edit classes, and prompt/model/schema
correlations. Both may emit **advisory recommendations** — but they never mutate production
detectors, prompts, schemas, algorithms, or Publisher-approved data. Any proposed change must enter
the governed approval workflow (the `governance` block states this on every output).

Outputs validate against `schemas/geometry_intelligence.schema.json` /
`schemas/metadata_intelligence.schema.json` (the shared contracts).
"""
import scout_report_index as sri
import scout_report_publisher as srp
import scout_benchmark as sb

GEOMETRY_INTELLIGENCE_CONTRACT_VERSION = "v1"
METADATA_INTELLIGENCE_CONTRACT_VERSION = "v1"

_GOVERNANCE = {
    "advisory_only": True,
    "note": ("Recommendations are advisory. Scout never changes detectors, prompts, models, schemas, "
             "algorithms, or Publisher-approved data. Any proposed change must enter the governed "
             "approval workflow with human authority as final."),
}
_GEOM_FAILURE_MODES = [  # (label, count-field, denominator-field)
    ("panel_splits", "panel_splits", "approved_panels_evaluated"),
    ("panel_merges", "panel_merges", "generated_panels_evaluated"),
    ("false_panels", "false_panels", "generated_panels_evaluated"),
    ("missing_page_panels", "missing_page_panels", "approved_panels_evaluated"),
    ("spread_missing_panels", "spread_missing_panels", "approved_panels_evaluated"),
]


def _rate(n, d):
    return round(n / d, 6) if d else 0.0


# --------------------------------------------------------------------------- #
# Geometry Intelligence
# --------------------------------------------------------------------------- #
def geometry_intelligence(entries, generated_at="1970-01-01T00:00:00Z", scope=None):
    """Domain projection for Geometry Intelligence (pure). Consumes report-index entries."""
    entries = [e for e in entries if (e.get("geometry_benchmark") or {})]
    proj = sb.build_projection(entries, scope or {"level": "platform"}, generated_at)
    gseg = proj["geometry"]["segments"]

    # Recurring failure modes per comparability segment (summed raw counts, ranked).
    by_key = {}
    axes_by_key = {}
    for e in entries:
        key = e.get("geometry_comparability_key")
        by_key.setdefault(key, []).append(e)
        axes_by_key[key] = (e.get("comparability") or {}).get("geometry_axes")
    recurring = []
    for key in sorted(k for k in by_key if k is not None):
        modes = []
        for label, cf, df in _GEOM_FAILURE_MODES:
            num = sum((e["geometry_benchmark"].get(cf) or 0) for e in by_key[key])
            den = sum((e["geometry_benchmark"].get(df) or 0) for e in by_key[key])
            modes.append({"mode": label, "count": num, "numerator": num, "denominator": den,
                          "rate": _rate(num, den)})
        modes.sort(key=lambda m: (-m["count"], m["mode"]))
        recurring.append({"comparability_key": key, "reports": len(by_key[key]), "modes": modes})

    # Version-correlated improvements: order segments by their earliest point, diff adjacent ones.
    seg_time = {}
    for p in proj["geometry"]["points"]:
        k = p["comparability_key"]
        t = p.get("measurement_time") or ""
        if k not in seg_time or t < seg_time[k]:
            seg_time[k] = t
    ordered = sorted((k for k in gseg), key=lambda k: (seg_time.get(k, ""), k))
    improvements = []
    for a, b in zip(ordered, ordered[1:]):
        changed = sri.comparability_diff(axes_by_key.get(a) or {}, axes_by_key.get(b) or {})
        deltas = {}
        for m in set(gseg[a]["metrics"]) & set(gseg[b]["metrics"]):
            ra, rb = gseg[a]["metrics"][m]["rate"], gseg[b]["metrics"][m]["rate"]
            if ra is not None and rb is not None:
                deltas[m] = {"from": ra, "to": rb, "delta": round(rb - ra, 6)}
        improvements.append({"from": a, "to": b, "changed_axes": changed, "metric_deltas": deltas,
                             "sample_sizes": {"from": gseg[a]["sample_sizes"],
                                              "to": gseg[b]["sample_sizes"]}})

    recommendations = []
    for seg in recurring:
        m = {x["mode"]: x for x in seg["modes"]}
        if m["panel_merges"]["rate"] > 0.5:
            recommendations.append({"code": "geometry.under_segmentation",
                "advice": "Automation merges panels humans keep separate at a high rate; propose a "
                          "detector re-segmentation review (governed).",
                "evidence": {"comparability_key": seg["comparability_key"],
                             "merge_rate": m["panel_merges"]["rate"], "reports": seg["reports"]}})
        if m["false_panels"]["rate"] > 0.15:
            recommendations.append({"code": "geometry.precision_gap",
                "advice": "Automation emits panels not present in approval; propose a precision review.",
                "evidence": {"comparability_key": seg["comparability_key"],
                             "false_rate": m["false_panels"]["rate"]}})

    return {
        "contract_version": GEOMETRY_INTELLIGENCE_CONTRACT_VERSION, "task": "geometry",
        "generated_at": generated_at, "scope": scope or {"level": "platform"},
        "sample_sizes": {"reports": len(entries),
                         "segments": len(gseg), "issues": proj["sample_sizes"]["issues"]},
        "segments": [dict(v) for v in gseg.values()],
        "recurring_failure_modes": recurring,
        "version_correlated_improvements": improvements,
        "recommendations": recommendations,
        "governance": dict(_GOVERNANCE),
    }


# --------------------------------------------------------------------------- #
# Metadata Intelligence
# --------------------------------------------------------------------------- #
_META_FIELDS = ("classification.tags", "entities.characters", "narrative.dialogue", "narrative.summary")


def metadata_intelligence(entries, reports_by_id, generated_at="1970-01-01T00:00:00Z", scope=None):
    """Domain projection for Metadata Intelligence (pure). Consumes report-index entries + the full
    immutable reports (for per-field detail). Only comparable (non-abstained) reports contribute."""
    comparable = [e for e in entries
                  if (e.get("metadata_benchmark") or {}).get("applicable")
                  and (e.get("metadata_benchmark") or {}).get("comparable_fields")]

    # Weak fields: weighted per-field accepted/edit rate across the comparable reports' per_field.
    field_acc, field_cmp, field_edit = {f: 0 for f in _META_FIELDS}, {f: 0 for f in _META_FIELDS}, {f: 0 for f in _META_FIELDS}
    for e in comparable:
        rep = reports_by_id.get(e.get("report_id"))
        pf = (((rep or {}).get("delta_report") or {}).get("metadata_benchmark") or {}).get("per_field") or {}
        for f in _META_FIELDS:
            agg = pf.get(f) or {}
            acc = (agg.get("accepted_unchanged_rate") or {})
            field_acc[f] += acc.get("numerator") or 0
            field_cmp[f] += acc.get("denominator") or 0
            counts = agg.get("counts") or {}
            field_edit[f] += sum(counts.get(c, 0) for c in
                                 ("minor_wording_edit", "moderate_rewrite", "major_rewrite",
                                  "complete_replacement", "added", "removed"))
    weak = []
    for f in _META_FIELDS:
        cmp_n = field_cmp[f]
        weak.append({"field": f, "comparable_fields": cmp_n,
                     "accepted_unchanged_rate": _rate(field_acc[f], cmp_n),
                     "edit_rate": _rate(field_edit[f], cmp_n),
                     "numerator": field_edit[f], "denominator": cmp_n})
    weak.sort(key=lambda w: (-w["edit_rate"], w["field"]))

    # Common edit classes: summed global category counts across comparable reports.
    classes = {}
    total_fields = 0
    for e in comparable:
        counts = (e["metadata_benchmark"].get("counts") or {})
        for c, n in counts.items():
            classes[c] = classes.get(c, 0) + n
        total_fields += e["metadata_benchmark"].get("comparable_fields") or 0

    # Prompt/model/schema correlations: group by the metadata comparability axes.
    groups = {}
    for e in comparable:
        ax = (e.get("comparability") or {}).get("metadata_axes") or {}
        gk = (ax.get("metadata_prompt_version"), ax.get("metadata_model"), ax.get("metadata_schema_version"))
        acc = (e["metadata_benchmark"].get("accepted_unchanged_rate") or {})
        g = groups.setdefault(gk, {"reports": 0, "num": 0, "den": 0})
        g["reports"] += 1
        g["num"] += acc.get("numerator") or 0
        g["den"] += acc.get("denominator") or 0
    correlations = []
    for (pv, model, schema), g in sorted(groups.items(), key=lambda kv: str(kv[0])):
        correlations.append({"group": {"prompt_version": pv, "model": model, "metadata_schema_version": schema},
                             "reports": g["reports"], "numerator": g["num"], "denominator": g["den"],
                             "accepted_unchanged_rate": _rate(g["num"], g["den"])})

    opportunities, recommendations = [], []
    for w in weak:
        if w["edit_rate"] > 0.4 and w["comparable_fields"] > 0:
            opportunities.append({"field": w["field"], "reason": "high editorial rework",
                                  "rate": w["edit_rate"]})
    if opportunities:
        recommendations.append({"code": "metadata.prompt_refinement",
            "advice": "Fields with high editorial rework are candidates for a prompt-refinement "
                      "proposal (governed); Scout does not modify prompts.",
            "evidence": {"fields": [o["field"] for o in opportunities]}})

    return {
        "contract_version": METADATA_INTELLIGENCE_CONTRACT_VERSION, "task": "metadata",
        "generated_at": generated_at, "scope": scope or {"level": "platform"},
        "sample_sizes": {"reports": len(entries), "comparable_reports": len(comparable)},
        "comparable_reports": len(comparable),
        "weak_fields": weak,
        "common_edit_classes": {"counts": classes, "total_comparable_fields": total_fields},
        "prompt_model_schema_correlations": correlations,
        "prompt_improvement_opportunities": opportunities,
        "recommendations": recommendations,
        "governance": dict(_GOVERNANCE),
    }


# --------------------------------------------------------------------------- #
# Loaders (consume the persisted contracts from edenseek-scout)
# --------------------------------------------------------------------------- #
def build_geometry_intelligence(client=None, generated_at="1970-01-01T00:00:00Z", context=None):
    index = sri.load_index(client, context=context)
    return geometry_intelligence(index.get("entries", []), generated_at,
                                 {"level": "issue", "issue_prefix": index.get("issue_prefix")})


def build_metadata_intelligence(client=None, generated_at="1970-01-01T00:00:00Z", context=None):
    index = sri.load_index(client, context=context)
    entries = index.get("entries", [])
    reports_by_id = {}
    for e in entries:
        if not ((e.get("metadata_benchmark") or {}).get("applicable")
                and (e.get("metadata_benchmark") or {}).get("comparable_fields")):
            continue
        key = (e.get("persisted_key") or {}).get("history")
        if not key:
            continue
        try:
            import json
            reports_by_id[e["report_id"]] = json.loads(srp.read_object(client, key, context=context))
        except Exception:  # noqa: BLE001 — a missing/unreadable report just drops from per-field detail
            continue
    return metadata_intelligence(entries, reports_by_id, generated_at,
                                 {"level": "issue", "issue_prefix": index.get("issue_prefix")})
