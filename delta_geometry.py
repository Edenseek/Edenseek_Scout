"""Deterministic generated-vs-approved GEOMETRY delta (Scout 6.3, Phase A).

Pure functions over Scout's canonical geometry model (produced by
``review_contract_adapter``) — no Publisher shapes, no I/O, no LLM/vision. Implements the
Stage-1(automated)-vs-Stage-2(approved) geometry metrics of
``SCOUT_APPROVAL_DELTA_ARCHITECTURE.md``: panels are matched by IoU overlap, and the delta is
precision / recall / split / merge / missing / false. Advisory only — the approved geometry
is the Human Approval Benchmark; automation is scored against it.
"""
from review_contract_adapter import APPLICABILITY_MANUAL

# Fixed IoU match threshold (named constant so the delta is reproducible and reviewable).
IOU_THRESHOLD = 0.5

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


def _match_stratum(gen, appr, scope_of, iou_threshold):
    """IoU-match one stratum (page or spread) WITHIN a scope, so a panel only matches others in the
    same page/spread. ``scope_of(entry)`` yields the scope key (page_number for page panels; the
    page_range tuple for spreads — their coordinates are normalized per page / per spread canvas and
    would otherwise collide). Returns counts + artifact-id lists in the shared delta vocabulary.
    Deterministic: ids processed in sorted order."""
    gen_ids, app_ids = sorted(gen), sorted(appr)
    gm = {g: [] for g in gen_ids}
    am = {a: [] for a in app_ids}
    for g in gen_ids:
        gb, gk = gen[g]["bbox"], scope_of(gen[g])
        for a in app_ids:
            if scope_of(appr[a]) == gk and _iou(gb, appr[a]["bbox"]) >= iou_threshold:
                gm[g].append(a)
                am[a].append(g)
    return {
        "n_gen": len(gen_ids),
        "n_app": len(app_ids),
        "matched_generated": sum(1 for g in gen_ids if gm[g]),
        "matched_approved": sum(1 for a in app_ids if am[a]),
        "false_artifact_ids": [g for g in gen_ids if not gm[g]],       # automation, no approval
        "missing_artifact_ids": [a for a in app_ids if not am[a]],     # approval, automation missed
        "split_artifact_ids": [a for a in app_ids if len(am[a]) > 1],  # 1 approved <- many automated
        "merge_artifact_ids": [g for g in gen_ids if len(gm[g]) > 1],  # 1 automated -> many approved
        "unchanged": sum(1 for a in app_ids
                         if len(am[a]) == 1 and len(gm[am[a][0]]) == 1),
    }


def _combine(*strata):
    """Micro-average combine of strata: sum counts, concatenate id lists (order-stable)."""
    out = {k: 0 for k in ("n_gen", "n_app", "matched_generated", "matched_approved", "unchanged")}
    for k in ("false_artifact_ids", "missing_artifact_ids", "split_artifact_ids", "merge_artifact_ids"):
        out[k] = []
    for s in strata:
        for k in ("n_gen", "n_app", "matched_generated", "matched_approved", "unchanged"):
            out[k] += s[k]
        for k in ("false_artifact_ids", "missing_artifact_ids", "split_artifact_ids", "merge_artifact_ids"):
            out[k] += s[k]
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
            "split_rate": _rate(len(s["split_artifact_ids"]), s["n_app"]),
            "merge_rate": _rate(len(s["merge_artifact_ids"]), s["n_gen"]),
            "false_count": len(s["false_artifact_ids"]),
            "missing_count": len(s["missing_artifact_ids"]),
            "unchanged_geometry_panels": s["unchanged"],
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
