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

# Version of the geometry MATCHING rules (IoU overlap match + split/merge/false/missing
# definitions). A comparability axis for the geometry benchmark: a change here (or to
# IOU_THRESHOLD) means new geometry metrics are not directly comparable to older ones.
GEOMETRY_MATCH_VERSION = "v1"


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


def compute_geometry_delta(canonical_review, iou_threshold=IOU_THRESHOLD):
    """Geometry delta for one canonical review. Manual publications are NOT-APPLICABLE
    (never a zero-delta). Deterministic: artifact ids are processed in sorted order."""
    if canonical_review.get("applicability") == APPLICABILITY_MANUAL:
        return {"applicable": False, "reason": "manual_publication",
                "note": "manual publication has no generated side; geometry delta is not applicable"}

    generated = canonical_review["generated"]["geometry"]
    approved = canonical_review["approved"]["geometry"]
    # Benchmark set excludes deleted approved panels. Spread panels are DRAWN — they have no
    # generated (auto page-space) counterpart — so they are never IoU-matched; they are always
    # approved-only / missing. They still count in the recall denominator (automation missed them).
    approved_page = sorted(aid for aid, e in approved.items()
                           if not e["flags"].get("deleted") and not e["flags"].get("is_spread"))
    approved_spread = sorted(aid for aid, e in approved.items()
                             if not e["flags"].get("deleted") and e["flags"].get("is_spread"))
    generated_ids = sorted(generated.keys())

    gen_matches = {gid: [] for gid in generated_ids}   # gid -> approved page ids it overlaps
    app_matches = {aid: [] for aid in approved_page}    # page aid -> generated ids overlapping it
    for gid in generated_ids:
        gb = generated[gid]["bbox"]
        for aid in approved_page:
            if _iou(gb, approved[aid]["bbox"]) >= iou_threshold:
                gen_matches[gid].append(aid)
                app_matches[aid].append(gid)

    matched_generated = [g for g in generated_ids if gen_matches[g]]
    matched_approved = [a for a in approved_page if app_matches[a]]
    split = [a for a in approved_page if len(app_matches[a]) > 1]    # 1 approved <- many automated
    merge = [g for g in generated_ids if len(gen_matches[g]) > 1]    # 1 automated -> many approved
    missing_page = [a for a in approved_page if not app_matches[a]]  # page panel automation missed
    false_panels = [g for g in generated_ids if not gen_matches[g]]  # automation with no approval
    missing = missing_page + approved_spread                        # spreads are always missing

    n_gen = len(generated_ids)
    n_app = len(approved_page) + len(approved_spread)   # spreads count against recall

    # Panels the human left unchanged: a clean 1:1 match (approved page panel with exactly one
    # automated match, whose automated panel maps only to it — neither split nor merge).
    unchanged = sum(1 for a in approved_page
                    if len(app_matches[a]) == 1 and len(gen_matches[app_matches[a][0]]) == 1)
    # Every divergence from automation the human approval represents (added/removed/split/merged).
    total_corrections = len(false_panels) + len(missing) + len(split) + len(merge)
    summary = (canonical_review.get("generated") or {}).get("summary") or {}
    pages = summary.get("total_story_pages") or summary.get("total_pages")
    if not pages:  # fall back to distinct generated page numbers
        pages = len({generated[g].get("page_number") for g in generated_ids
                     if generated[g].get("page_number") is not None})

    def _ratio(numer, denom):
        return {"numerator": numer, "denominator": denom, "rate": _rate(numer, denom)}

    return {
        "applicable": True,
        "iou_threshold": iou_threshold,
        "geometry_match_version": GEOMETRY_MATCH_VERSION,
        "generated_panel_count": n_gen,
        "approved_panel_count": n_app,
        "approved_spread_count": len(approved_spread),
        "precision": _rate(len(matched_generated), n_gen),
        "recall": _rate(len(matched_approved), n_app),
        "split_rate": _rate(len(split), n_app),
        "merge_rate": _rate(len(merge), n_gen),
        "missing_count": len(missing),
        "missing_rate": _rate(len(missing), n_app),   # == 1 - recall
        "false_count": len(false_panels),
        "false_rate": _rate(len(false_panels), n_gen),  # == 1 - precision
        "missing_artifact_ids": missing,
        "missing_page_artifact_ids": missing_page,
        "spread_missing_artifact_ids": approved_spread,
        "false_artifact_ids": false_panels,
        "split_artifact_ids": split,
        "merge_artifact_ids": merge,
        # Raw counts + numerator/denominator pairs so every rate is independently reproducible.
        "benchmark": {
            "true_matches": len(matched_approved),          # approved page panels correctly detected
            "matched_generated": len(matched_generated),
            "matched_approved": len(matched_approved),
            "generated_panels_evaluated": n_gen,
            "approved_panels_evaluated": n_app,
            "approved_page_panels": len(approved_page),
            "approved_spread_panels": len(approved_spread),
            "panel_splits": len(split),
            "panel_merges": len(merge),
            "false_panels": len(false_panels),
            "missing_panels": len(missing),
            "missing_page_panels": len(missing_page),
            "spread_missing_panels": len(approved_spread),
            "unchanged_geometry_panels": unchanged,
            "total_human_geometry_corrections": total_corrections,
            "pages_evaluated": pages,
            "corrections_per_page": _rate(total_corrections, pages),
            "unchanged_geometry_rate": _rate(unchanged, n_app),
            "ratios": {
                "precision": _ratio(len(matched_generated), n_gen),
                "recall": _ratio(len(matched_approved), n_app),
                "split_rate": _ratio(len(split), n_app),
                "merge_rate": _ratio(len(merge), n_gen),
                "false_rate": _ratio(len(false_panels), n_gen),
                "missing_rate": _ratio(len(missing), n_app),
                "unchanged_geometry_rate": _ratio(unchanged, n_app),
            },
        },
    }
