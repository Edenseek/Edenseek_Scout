"""Deterministic generated-vs-approved GEOMETRY delta (Scout 6.3, Phase A).

Pure functions over Scout's canonical geometry model (produced by
``review_contract_adapter``) — no Publisher shapes, no I/O, no LLM/vision. Implements the
Stage-1(automated)-vs-Stage-2(approved) geometry metrics of
``SCOUT_APPROVAL_DELTA_ARCHITECTURE.md``: panels are matched by IoU overlap, and the delta is
precision / recall / split / merge / missing / false. Advisory only — the approved geometry
is the Human Approval Benchmark; automation is scored against it.
"""
import statistics

from review_contract_adapter import APPLICABILITY_MANUAL

# Fixed IoU match threshold (named constant so the delta is reproducible and reviewable).
IOU_THRESHOLD = 0.5

# Target band for the quality-weighted segmentation accuracy the pipeline drives toward.
GEOMETRY_ACCURACY_TARGET_LOW = 0.95
GEOMETRY_ACCURACY_TARGET_HIGH = 0.99

# Version of the geometry MATCHING rules (per-page IoU overlap match + split/merge/false/missing
# definitions). A comparability axis for the geometry benchmark: a change here (or to
# IOU_THRESHOLD) means new geometry metrics are not directly comparable to older ones.
# v2: the corrected, STRATIFIED geometry model. Matching is scoped: page panels match within a page
# (by page_number); spread panels match within a spread (by page_range) in the spread-canvas frame —
# so same-position panels on different pages/spreads never falsely match. Whole-issue precision/recall
# are the micro-average of the page + spread strata; each stratum is also reported.
# See docs/phases/geometry-correctness/CROSS_PAGE_MATCHING_DEFECT.md.
GEOMETRY_MATCH_VERSION = "v2"


def _iou(a, b):
    """Intersection-over-union of two ``(x, y, w, h)`` boxes. Degenerate/zero-area -> 0.0."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    if inter <= 0.0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0.0 else 0.0


def _rate(numer, denom):
    return round(numer / denom, 6) if denom else 0.0


def _resize_diag(approved_id, generated_id, iou, abox, gbox):
    """Per matched-panel geometry discrepancy — how the human resized/moved the automated box: the
    IoU (match quality / partial credit), the area ratio (generated/approved), and per-edge deltas.
    All in the shared normalized frame; a positive width/height error = automation drew it too big,
    negative = too small."""
    ax, ay, aw, ah = abox
    gx, gy, gw, gh = gbox
    area_a, area_g = aw * ah, gw * gh

    def _pct(g_v, a_v):
        return round((g_v - a_v) / a_v, 6) if a_v else None

    return {
        "approved_id": approved_id, "generated_id": generated_id,
        "iou": round(iou, 6),
        "area_ratio": round(area_g / area_a, 6) if area_a else None,
        "dx": round(gx - ax, 6), "dy": round(gy - ay, 6),
        "dw_pct": _pct(gw, aw), "dh_pct": _pct(gh, ah),
    }


def _match_stratum(gen, appr, scope_of, iou_threshold):
    """IoU-match one stratum (page or spread) WITHIN a scope, so a panel only matches others in the
    same page/spread. ``scope_of(entry)`` yields the scope key (page_number for page panels; the
    page_range tuple for spreads — their coordinates are normalized per page / per spread canvas and
    would otherwise collide). Returns counts + artifact-id lists in the shared delta vocabulary.

    Also computes, per matched approved panel, the quality of its BEST (highest-IoU) generated match
    — continuous IoU (partial credit) + resize diagnostics — and the stratum's earned credit
    E = sum of those qualities (the numerator of the quality-weighted segmentation accuracy).
    Deterministic: ids processed in sorted order."""
    gen_ids, app_ids = sorted(gen), sorted(appr)
    gm = {g: [] for g in gen_ids}
    am = {a: [] for a in app_ids}
    best = {}   # approved id -> (iou, generated id) of its best (highest-IoU) match
    for g in gen_ids:
        gb, gk = gen[g]["bbox"], scope_of(gen[g])
        for a in app_ids:
            if scope_of(appr[a]) != gk:
                continue
            iou = _iou(gb, appr[a]["bbox"])
            if iou >= iou_threshold:
                gm[g].append(a)
                am[a].append(g)
                if a not in best or iou > best[a][0]:
                    best[a] = (iou, g)
    matched_app = [a for a in app_ids if am[a]]
    pairs = [_resize_diag(a, best[a][1], best[a][0], appr[a]["bbox"], gen[best[a][1]]["bbox"])
             for a in matched_app]
    return {
        "n_gen": len(gen_ids),
        "n_app": len(app_ids),
        "matched_generated": sum(1 for g in gen_ids if gm[g]),
        "matched_approved": len(matched_app),
        "false_artifact_ids": [g for g in gen_ids if not gm[g]],       # automation, no approval
        "missing_artifact_ids": [a for a in app_ids if not am[a]],     # approval, automation missed
        "split_artifact_ids": [a for a in app_ids if len(am[a]) > 1],  # 1 approved <- many automated
        "merge_artifact_ids": [g for g in gen_ids if len(gm[g]) > 1],  # 1 automated -> many approved
        "unchanged": sum(1 for a in app_ids
                         if len(am[a]) == 1 and len(gm[am[a][0]]) == 1),
        "earned_credit": round(sum(best[a][0] for a in matched_app), 6),
        "matched_pairs": pairs,
    }


def _resize_bias(pairs):
    """Aggregate (systematic) resize bias over matched panels — surfaces e.g. 'boxes consistently
    ~15% too narrow'. Mean + median of the area ratio and per-edge width/height error."""
    def _agg(key):
        vals = [p[key] for p in pairs if p.get(key) is not None]
        return ({"mean": round(statistics.fmean(vals), 6), "median": round(statistics.median(vals), 6)}
                if vals else None)
    return {"matched": len(pairs), "area_ratio": _agg("area_ratio"),
            "dw_pct": _agg("dw_pct"), "dh_pct": _agg("dh_pct")}


def _seg_accuracy(stratum):
    """Quality-weighted segmentation accuracy = E / (A + FP): earned IoU credit over the union of the
    approved set (each worth 1.0) and the false automated panels. 1.0 only at perfect reproduction
    (every approved panel matched at IoU 1, nothing missing, nothing false); monotonic — the score
    the 95-99% target tracks."""
    earned = stratum["earned_credit"]
    denom = stratum["n_app"] + len(stratum["false_artifact_ids"])   # A + FP (soft-Jaccard union)
    score = _rate(earned, denom)
    return {"numerator": earned, "denominator": denom, "score": score,
            "target_low": GEOMETRY_ACCURACY_TARGET_LOW, "target_high": GEOMETRY_ACCURACY_TARGET_HIGH,
            "meets_target": score >= GEOMETRY_ACCURACY_TARGET_LOW}


def _combine(*strata):
    """Micro-average combine of strata: sum counts + earned credit, concatenate id lists / pairs."""
    _ids = ("false_artifact_ids", "missing_artifact_ids", "split_artifact_ids",
            "merge_artifact_ids", "matched_pairs")
    out = {k: 0 for k in ("n_gen", "n_app", "matched_generated", "matched_approved", "unchanged")}
    out["earned_credit"] = 0.0
    for k in _ids:
        out[k] = []
    for s in strata:
        for k in ("n_gen", "n_app", "matched_generated", "matched_approved", "unchanged"):
            out[k] += s[k]
        out["earned_credit"] += s["earned_credit"]
        for k in _ids:
            out[k] += s[k]
    out["earned_credit"] = round(out["earned_credit"], 6)
    return out


def compute_geometry_delta(canonical_review, iou_threshold=IOU_THRESHOLD):
    """Geometry delta for one canonical review. Manual publications are NOT-APPLICABLE
    (never a zero-delta). Deterministic: artifact ids are processed in sorted order."""
    if canonical_review.get("applicability") == APPLICABILITY_MANUAL:
        return {"applicable": False, "reason": "manual_publication",
                "note": "manual publication has no generated side; geometry delta is not applicable"}

    generated = canonical_review["generated"]["geometry"]
    approved = canonical_review["approved"]["geometry"]
    # Two strata, each matched WITHIN its own scope. PAGE panels are matched within a page
    # (page_number); SPREAD panels are matched within a spread (page_range) in the spread-canvas
    # frame. Coordinates are normalized per page / per spread, so cross-page and cross-spread
    # collisions must never match. The whole-issue metric is the micro-average of the two strata
    # (sum of numerators/denominators; every panel counts as 1.0); each stratum is also reported.
    gen_page = {g: e for g, e in generated.items() if not e["flags"].get("is_spread")}
    gen_spread = {g: e for g, e in generated.items() if e["flags"].get("is_spread")}
    appr_page = {a: e for a, e in approved.items()
                 if not e["flags"].get("deleted") and not e["flags"].get("is_spread")}
    appr_spread = {a: e for a, e in approved.items()
                   if not e["flags"].get("deleted") and e["flags"].get("is_spread")}

    page = _match_stratum(gen_page, appr_page, lambda e: e.get("page_number"), iou_threshold)
    spread = _match_stratum(gen_spread, appr_spread,
                            lambda e: tuple(e.get("page_range") or []), iou_threshold)
    total = _combine(page, spread)

    summary = (canonical_review.get("generated") or {}).get("summary") or {}
    pages = summary.get("total_story_pages") or summary.get("total_pages")
    if not pages:  # fall back to distinct generated page numbers (page + spread rows)
        pages = len({generated[g].get("page_number") for g in generated
                     if generated[g].get("page_number") is not None})
    total_corrections = (len(total["false_artifact_ids"]) + len(total["missing_artifact_ids"])
                         + len(total["split_artifact_ids"]) + len(total["merge_artifact_ids"]))

    def _ratio(numer, denom):
        return {"numerator": numer, "denominator": denom, "rate": _rate(numer, denom)}

    def _stratum_metrics(s):
        return {
            "generated_panel_count": s["n_gen"],
            "approved_panel_count": s["n_app"],
            "precision": _rate(s["matched_generated"], s["n_gen"]),
            "recall": _rate(s["matched_approved"], s["n_app"]),
            "segmentation_accuracy": _seg_accuracy(s),   # quality-weighted E/(A+FP)
            "split_rate": _rate(len(s["split_artifact_ids"]), s["n_app"]),
            "merge_rate": _rate(len(s["merge_artifact_ids"]), s["n_gen"]),
            "false_count": len(s["false_artifact_ids"]),
            "missing_count": len(s["missing_artifact_ids"]),
            "unchanged_geometry_panels": s["unchanged"],
            "resize_bias": _resize_bias(s["matched_pairs"]),
            "matched_pairs": s["matched_pairs"],   # per-panel IoU + resize diagnostics
            "missing_artifact_ids": s["missing_artifact_ids"],
            "false_artifact_ids": s["false_artifact_ids"],
            "split_artifact_ids": s["split_artifact_ids"],
            "merge_artifact_ids": s["merge_artifact_ids"],
        }

    return {
        "applicable": True,
        "iou_threshold": iou_threshold,
        "geometry_match_version": GEOMETRY_MATCH_VERSION,
        # ---- whole-issue TOTAL (page + spread strata, micro-averaged) ----
        "generated_panel_count": total["n_gen"],
        "approved_panel_count": total["n_app"],
        "approved_spread_count": spread["n_app"],
        "precision": _rate(total["matched_generated"], total["n_gen"]),
        "recall": _rate(total["matched_approved"], total["n_app"]),
        "segmentation_accuracy": _seg_accuracy(total),   # headline quality-weighted E/(A+FP)
        "resize_bias": _resize_bias(total["matched_pairs"]),
        "split_rate": _rate(len(total["split_artifact_ids"]), total["n_app"]),
        "merge_rate": _rate(len(total["merge_artifact_ids"]), total["n_gen"]),
        "missing_count": len(total["missing_artifact_ids"]),
        "missing_rate": _rate(len(total["missing_artifact_ids"]), total["n_app"]),  # == 1 - recall
        "false_count": len(total["false_artifact_ids"]),
        "false_rate": _rate(len(total["false_artifact_ids"]), total["n_gen"]),      # == 1 - precision
        "missing_artifact_ids": total["missing_artifact_ids"],
        "false_artifact_ids": total["false_artifact_ids"],
        "split_artifact_ids": total["split_artifact_ids"],
        "merge_artifact_ids": total["merge_artifact_ids"],
        # page/spread-specific id lists — the correction ledger + manifest distinguish the two.
        "missing_page_artifact_ids": page["missing_artifact_ids"],
        "spread_missing_artifact_ids": spread["missing_artifact_ids"],
        # ---- per-stratum breakdown (page vs spread sub-groups) ----
        "strata": {"page": _stratum_metrics(page), "spread": _stratum_metrics(spread)},
        # Raw counts + numerator/denominator pairs so every rate is independently reproducible.
        "benchmark": {
            "true_matches": total["matched_approved"],
            "matched_generated": total["matched_generated"],
            "matched_approved": total["matched_approved"],
            "generated_panels_evaluated": total["n_gen"],
            "approved_panels_evaluated": total["n_app"],
            "page_generated_panels": page["n_gen"],
            "page_approved_panels": page["n_app"],
            "spread_generated_panels": spread["n_gen"],
            "spread_approved_panels": spread["n_app"],
            "panel_splits": len(total["split_artifact_ids"]),
            "panel_merges": len(total["merge_artifact_ids"]),
            "false_panels": len(total["false_artifact_ids"]),
            "missing_panels": len(total["missing_artifact_ids"]),
            "missing_page_panels": len(page["missing_artifact_ids"]),
            "spread_missing_panels": len(spread["missing_artifact_ids"]),
            "unchanged_geometry_panels": total["unchanged"],
            "total_human_geometry_corrections": total_corrections,
            "pages_evaluated": pages,
            "corrections_per_page": _rate(total_corrections, pages),
            "unchanged_geometry_rate": _rate(total["unchanged"], total["n_app"]),
            "ratios": {
                "precision": _ratio(total["matched_generated"], total["n_gen"]),
                "recall": _ratio(total["matched_approved"], total["n_app"]),
                "segmentation_accuracy": _ratio(total["earned_credit"],
                                                total["n_app"] + len(total["false_artifact_ids"])),
                "split_rate": _ratio(len(total["split_artifact_ids"]), total["n_app"]),
                "merge_rate": _ratio(len(total["merge_artifact_ids"]), total["n_gen"]),
                "false_rate": _ratio(len(total["false_artifact_ids"]), total["n_gen"]),
                "missing_rate": _ratio(len(total["missing_artifact_ids"]), total["n_app"]),
                "unchanged_geometry_rate": _ratio(total["unchanged"], total["n_app"]),
            },
            "strata": {
                "page": {"precision": _ratio(page["matched_generated"], page["n_gen"]),
                         "recall": _ratio(page["matched_approved"], page["n_app"])},
                "spread": {"precision": _ratio(spread["matched_generated"], spread["n_gen"]),
                           "recall": _ratio(spread["matched_approved"], spread["n_app"])},
            },
        },
    }
