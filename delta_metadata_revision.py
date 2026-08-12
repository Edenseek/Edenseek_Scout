"""Deterministic, versioned metadata REVISION-DISTANCE benchmark (Scout reporting Increment 1).

Classifies how the creator/publisher approval revised each automated metadata field, per artifact
and per field, into a versioned category taxonomy — using only deterministic lexical/structural
measures (NO LLM). It compares Scout's canonical generated vs approved metadata (produced by the
anti-corruption adapter) BEFORE any further revision.

Governance: Scout stores **references + content hashes only** — never the raw generated/approved
metadata text. The authoritative values live in the immutable Publisher Review Record, addressable
by (review_id, artifact_id, field). Every underlying measure, numerator, denominator, and hash is
preserved so the categories can be recomputed after real editorial examples are reviewed.

Versioning: ``METADATA_REVISION_DISTANCE_VERSION`` stamps the thresholds + weights + the distance
definition. It is a metadata comparability axis — a change is a methodology boundary, never a silent
re-scoring. The thresholds/weights below are **provisional v1 defaults**. If an LLM-assisted semantic
scorer is added later it is an ADDITIONAL field beside these measures, never the authoritative scorer.

The distinction between an editorial rewording and a factual/complete replacement is first-class:
``minor_wording_edit`` is a separate category (and weight) from ``complete_replacement``.
"""
import hashlib
import json
import statistics

from review_contract_adapter import APPLICABILITY_MANUAL

# The distance DEFINITION (thresholds/weights/normalized char-Levenshtein over canonical rendering) is
# unchanged across v1.1 and the Panel Intelligence v2 field set — the canonical rendering handles both the
# v1.1 shapes and v2's structured dialogue generically. The v1.1↔v2 field-set boundary is carried by the
# evidence-dependent `metadata_schema_version` axis (v1.1/v1.1 vs v2/v2), NOT this code-methodology version,
# so v1.1 revisions keep auditing identically (no spurious boundary / re-run) after adapter v3.
METADATA_REVISION_DISTANCE_VERSION = "v1"  # PROVISIONAL — thresholds/weights subject to review

# The v1.1 canonical content fields (kept for the v1.1 series + reference).
FIELDS = ("classification.tags", "entities.characters", "narrative.dialogue", "narrative.summary")

# The v2 LLM-editorial leaves (per-leaf granularity: `classification.tags` is decomposed into facets,
# `setting`→`entities.environment`, dialogue restructured, objects/shot_type/weather/time_of_day added).
# Non-editorial fields (computed `classification.colors`, publisher `publisher_notes`) are NOT here — the
# adapter routes them out of the compared set via the Publisher `field_sources` marker.
V2_LLM_LEAVES = ("entities.characters", "entities.objects", "entities.environment",
                 "narrative.summary", "narrative.dialogue", "classification.shot_type",
                 "classification.tags.mood", "classification.tags.action",
                 "classification.tags.weather", "classification.tags.time_of_day")


def _field_list(generated):
    """The compared field set = exactly the editorial leaves the adapter extracted on the GENERATED side
    (what Scout audits). Data-driven, so a leaf the Publisher marks non-`llm` in `field_sources` (routed to
    `non_editorial`) is simply absent from the compared set — never a phantom abstention. For v1.1 this is
    the four fixed fields; for v2 the per-leaf set minus any marker-excluded leaves."""
    keys = set()
    for e in generated.values():
        keys.update((e.get("fields") or {}).keys())
    return sorted(keys)


def _schema_version_of(side_map):
    return next((e.get("schema_version") for e in side_map.values()), None)

# Provisional category thresholds on the normalized [0,1] primary distance (char-level Levenshtein
# over a canonical string rendering). d == 0 is an exact match.
T_MINOR = 0.10       # <= : a wording/punctuation/casing adjustment
T_MODERATE = 0.35    # <= : a moderate rewrite
T_MAJOR = 0.70       # <= : a major rewrite; above -> complete_replacement

# Provisional editorial-intervention weights per category (0 = no intervention, 1 = maximal).
WEIGHTS = {
    "accepted_unchanged": 0.0,
    "minor_wording_edit": 0.25,
    "moderate_rewrite": 0.5,
    "major_rewrite": 0.75,
    "complete_replacement": 1.0,
    "added": 0.5,      # approval populated a field automation left empty
    "removed": 1.0,    # approval discarded a field automation produced
}
# Categories that carry a numeric editorial distance (used for avg/median distance).
_DISTANCE_CATEGORIES = set(WEIGHTS)  # everything scored; abstention/unsupported are excluded
_EDIT_CATEGORIES = ("minor_wording_edit", "moderate_rewrite", "major_rewrite",
                    "complete_replacement", "added", "removed")

# ---- Metadata Headline Accuracy v2 ----
# Headline = field ACCEPTANCE rate (fields the human took with NO edit) — the "few edits to the
# publisher's satisfaction" metric: field-agnostic, deterministic, and it moves exactly with human
# editing effort. Target band 0.75-0.90. The per-field EDITORIAL BURDEN (which field costs the most
# edits) is the signal that drives prompt improvement / reduces publisher work. Edit-effort per field
# uses a DATA-DRIVEN distance (set-Jaccard where the field is a list/dict, token-Jaccard for text), so
# it stays correct as fields change — never keyed on a specific field name.
#
# v2 (metadata interface evolution, NOT a content/workflow change): acceptance is measured ONLY over
# FRESH generated outputs — the true first-pass LLM "before" state. The Publisher now emits a per-output
# `metadata_generation_provenance` disposition (fresh | preserved_approved | preserved_prior_success);
# `preserved_*` outputs equal prior approved content by construction, so counting them as "accepted"
# would inflate the rate. v2 excludes them from the denominator via the emitted flag rather than the
# invisible generate-before-approve invariant v1 implicitly relied on. Absent disposition (legacy
# revisions with no flag) is treated as fresh, so v2 is BACKWARD-IDENTICAL to v1 on all-fresh data.
# v3 (REVISION-AWARE denominator): on a REVISION, metadata is INHERITED, not generated — but an inherited
# output keeps its ORIGINAL `metadata_generation_provenance`, so a rev-1 `fresh` output still reads `fresh` in
# rev 2 though no LLM ran. Filtering on that flag alone would admit carried-forward content and produce a
# meaningless acceptance rate. v3 counts only content an LLM produced in THIS revision, using the composite
# rule below (`_counts_toward_acceptance`): the Publisher writes an `origin` field ONLY on the
# revision-inheritance path, so its PRESENCE (not value) discriminates. Absent origin -> generation path ->
# today's fresh-only filter (so v3 is NUMBER-IDENTICAL to v2 on first publications, where origin is absent
# on all outputs). Present origin -> revision-inherited -> exclude unless origin in {generated, regenerated}
# (i.e. today: excluded — carried_forward/confirmed/null all excluded). The version bump signals the
# methodology change; certified v2 first-publication numbers are unaffected (a re-audit re-derives the same
# denominator; the empty `origin:null` add/split/merge class contributes no content and is excluded).
METADATA_ACCURACY_VERSION = "v3"
METADATA_ACCURACY_TARGET_LOW = 0.75
METADATA_ACCURACY_TARGET_HIGH = 0.90

# Origin values that mean "an LLM produced this output IN THIS revision" (ratified vocab; not emitted yet).
_LLM_GENERATED_THIS_REVISION_ORIGINS = ("generated", "regenerated")


def _counts_toward_acceptance(r):
    """v3 revision-aware inclusion: does this field-record's output count toward the acceptance denominator —
    i.e. did an LLM produce it in THIS revision? Composite rule (Publisher-confirmed shapes):
      * `origin` ABSENT (generation path — first publication, or an in-revision regeneration returns a fresh
        output object without `origin`): use the v2 fresh-only filter (disposition fresh / None-legacy).
      * `origin` PRESENT (revision-inheritance path): count only ``generated``/``regenerated`` (LLM ran this
        cycle); EXCLUDE ``carried_forward``, ``confirmed``, and the empty ``null`` add/split/merge class.
    On a first publication `origin` is absent on every output, so this is identical to the v2 filter."""
    if not r.get("generated_has_origin"):
        return r.get("generated_disposition") in (None, "fresh")
    return r.get("generated_origin") in _LLM_GENERATED_THIS_REVISION_ORIGINS


def _is_empty(v):
    return v is None or v == "" or v == [] or v == {}


def _canon(value):
    """A canonical, deterministic string rendering of any field value (str/list/dict/None) — the
    basis for the lexical distance. Order-stable (sorted dict keys)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_canon(x) for x in value)
    if isinstance(value, dict):
        return "\n".join(f"{k}={_canon(value[k])}" for k in sorted(value, key=str))
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _sha256(value):
    """Stable content hash of a field value (a reference to the authoritative value, not a copy)."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _levenshtein(a, b):
    """Classic edit distance (two-row DP). Deterministic; no external deps."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _tokens(s):
    return [t for t in s.replace("\n", " ").split(" ") if t]


def _jaccard_distance(a_items, b_items):
    a, b = set(a_items), set(b_items)
    if not a and not b:
        return 0.0
    return round(1 - len(a & b) / len(a | b), 6)


def _elements(value):
    """Comparable elements for set-based structural distance (list elements / dict k=v pairs)."""
    if isinstance(value, list):
        return [_canon(x) for x in value]
    if isinstance(value, dict):
        return [f"{k}={_canon(value[k])}" for k in value]
    return None


def _measures(gen, app):
    """All underlying lexical + structural measures for one field pair (preserved for re-scoring)."""
    cg, ca = _canon(gen), _canon(app)
    max_len = max(len(cg), len(ca))
    char_lev = _levenshtein(cg, ca)
    ge, ae = _elements(gen), _elements(app)
    return {
        "char_levenshtein": char_lev,
        "char_levenshtein_norm": round(char_lev / max_len, 6) if max_len else 0.0,
        "token_jaccard_distance": _jaccard_distance(_tokens(cg), _tokens(ca)),
        "set_jaccard_distance": (_jaccard_distance(ge, ae) if ge is not None and ae is not None
                                 else None),
        "len_ratio": round(min(len(cg), len(ca)) / max_len, 6) if max_len else 1.0,
        "structural_equal": gen == app,
        "generated_type": type(gen).__name__,
        "approved_type": type(app).__name__,
    }


def _classify(gen, app):
    """Return (category, distance_or_None, measures) for one generated→approved field pair."""
    g_empty, a_empty = _is_empty(gen), _is_empty(app)
    if g_empty and a_empty:
        return "abstention", None, None                 # nothing on either side to evaluate
    if g_empty and not a_empty:
        return "added", 1.0, _measures(gen, app)          # approval populated an empty field
    if not g_empty and a_empty:
        return "removed", 1.0, _measures(gen, app)        # approval discarded automation's field
    m = _measures(gen, app)
    d = m["char_levenshtein_norm"]
    # Acceptance is gated on STRUCTURAL equality (the ground truth: gen == app), never on d == 0 alone.
    # The canonical rendering is not injective for adversarial content (embedded "\n"/"=" could make two
    # different structured-dialogue values share a canonical string, d == 0); such a collision is a real
    # edit, so it falls through to the distance buckets rather than a false accept.
    if m["structural_equal"]:
        cat = "accepted_unchanged"
    elif d <= T_MINOR:
        cat = "minor_wording_edit"
    elif d <= T_MODERATE:
        cat = "moderate_rewrite"
    elif d <= T_MAJOR:
        cat = "major_rewrite"
    else:
        cat = "complete_replacement"
    return cat, (0.0 if cat == "accepted_unchanged" else d), m


def _ratio(numer, denom):
    return {"numerator": numer, "denominator": denom,
            "rate": round(numer / denom, 6) if denom else 0.0}


def _empty_tally():
    return {c: 0 for c in ("accepted_unchanged", "minor_wording_edit", "moderate_rewrite",
                           "major_rewrite", "complete_replacement", "removed", "added",
                           "abstention", "unsupported_schema")}


def _aggregate(tally, distances, weighted_sum, gen_populated, app_populated, artifacts):
    """Numerator/denominator-preserving aggregates for a tally (global or per-field)."""
    comparable = sum(tally[c] for c in _DISTANCE_CATEGORIES)   # scored fields (excl. abstention/unsupported)
    edits = sum(tally[c] for c in _EDIT_CATEGORIES)
    return {
        "counts": dict(tally),
        "fields_generated": gen_populated,
        "fields_approved": app_populated,
        "comparable_fields": comparable,
        "accepted_unchanged_rate": _ratio(tally["accepted_unchanged"], comparable),
        "minor_wording_edit_rate": _ratio(tally["minor_wording_edit"], comparable),
        "moderate_rewrite_rate": _ratio(tally["moderate_rewrite"], comparable),
        "major_rewrite_rate": _ratio(tally["major_rewrite"], comparable),
        "complete_replacement_rate": _ratio(tally["complete_replacement"], comparable),
        "added_rate": _ratio(tally["added"], comparable),
        "removed_rate": _ratio(tally["removed"], comparable),
        "unchanged_metadata_rate": _ratio(tally["accepted_unchanged"], comparable),
        "weighted_editorial_intervention_score": {
            "numerator": round(weighted_sum, 6), "denominator": comparable,
            "score": round(weighted_sum / comparable, 6) if comparable else 0.0},
        # revision_distance_sum + count let higher-level projections compute an EXACT count-weighted
        # mean (never a mean-of-means): weighted avg = sum(distance_sum) / sum(comparable_fields).
        "revision_distance_sum": round(sum(distances), 6),
        "average_revision_distance": round(statistics.fmean(distances), 6) if distances else 0.0,
        "median_revision_distance": round(statistics.median(distances), 6) if distances else 0.0,
        "corrections_per_artifact": _ratio(edits, artifacts),
    }


def _aggregate_records(recs, artifacts):
    """Re-aggregate a SUBSET of revision-distance records (e.g. the FRESH-only subset) with the same
    numerator/denominator preservation as ``_aggregate``. Lets the certified headline be computed on
    the fresh denominator while the all-common ``global`` block stays a faithful descriptive record."""
    tally, distances, weighted = _empty_tally(), [], 0.0
    gen_pop = app_pop = 0
    for r in recs:
        cat = r["category"]
        tally[cat] += 1
        if not r["generated_empty"]:
            gen_pop += 1
        if not r["approved_empty"]:
            app_pop += 1
        if cat in WEIGHTS:
            weighted += WEIGHTS[cat]
        if r["distance"] is not None:
            distances.append(r["distance"])
    return _aggregate(tally, distances, weighted, gen_pop, app_pop, artifacts)


def _field_effort(records_for_field):
    """Type-appropriate edit effort over a field's EDITED records: set-Jaccard for list/dict fields
    (chosen from the DATA — set_jaccard present), token-Jaccard for text. Field-agnostic: the basis
    follows the value shape, so a new field gets the right method automatically. Returns (mean, method)."""
    vals, method = [], None
    for r in records_for_field:
        if r.get("category") not in _EDIT_CATEGORIES:
            continue
        m = r.get("measures") or {}
        if m.get("set_jaccard_distance") is not None:
            vals.append(m["set_jaccard_distance"]); method = "set_jaccard"
        elif m.get("token_jaccard_distance") is not None:
            vals.append(m["token_jaccard_distance"]); method = method or "token_jaccard"
    return (round(statistics.fmean(vals), 6) if vals else 0.0), method


def _calls_metric(counts):
    """"LLM calls per panel" from the per-panel recall counter (generation_provenance.generation_count).
    Best-effort — only over the artifacts that carry a count. A count > 1 means the panel was recalled."""
    vals = [v for v in counts.values() if isinstance(v, (int, float))]
    if not vals:
        return None
    return {"panels_with_count": len(vals), "total_calls": sum(vals),
            "mean_calls_per_panel": round(statistics.fmean(vals), 6),
            "max_calls": max(vals), "recalled_panels": sum(1 for v in vals if v > 1)}


def _metadata_accuracy(records, fresh_global, fields):
    """Metadata Headline Accuracy v2. Headline = field ACCEPTANCE rate (accepted / comparable) over the
    FRESH generated outputs only — the true first-pass LLM 'before' state. Preserved outputs
    (``generated_disposition`` in {preserved_approved, preserved_prior_success}) equal prior approved
    content by construction and are EXCLUDED from the denominator so they cannot inflate acceptance;
    absent disposition (legacy revisions) is treated as fresh, making v2 backward-identical on all-fresh
    data. ``fresh_global`` is the fresh-only ``_aggregate`` (the certified descriptive surface — the
    report headline sources from it so it never contradicts this acceptance number). Plus the per-field
    EDITORIAL BURDEN (which field costs the most edits + its share + edit effort). Field-agnostic; derived
    purely from the certified revision-distance records.

    Provenance-coverage gate (v2): when the disposition flag is present on only SOME outputs (``partial``,
    a Publisher-contract violation) the fresh/preserved split cannot be trusted, so ``meets_target`` is
    withheld (``None``) and ``provisional`` is set rather than emitting a green target off contaminated data.
    """
    is_fresh = _counts_toward_acceptance   # v3: revision-aware (origin-composite); v2 fresh-only when origin absent
    scored = [r for r in records if r.get("category") in _DISTANCE_CATEGORIES]
    fresh = [r for r in scored if is_fresh(r)]
    excluded = [r for r in scored if not is_fresh(r)]
    # Disposition coverage — the backward-compat default (absent -> fresh) is only safe when the disposition
    # flag is UNIFORMLY present or absent AMONG THE GENERATION-PATH OUTPUTS (origin absent). v3-aware: the
    # revision-inheritance outputs (origin present, incl. the empty add/split/merge class which legitimately
    # carries NO disposition) are excluded from this check — they are keyed on `origin`, not the disposition,
    # so a missing disposition there is contract-conformant, not a "partial emission" violation. Restricting
    # to generation-path records is what stops a legitimate mixed revision (a regenerated output + an empty
    # add) from falsely reading "partial" and withholding meets_target.
    gen_path = [r for r in records if not r.get("generated_has_origin")]
    flagged = sum(1 for r in gen_path if r.get("generated_disposition") is not None)
    if not gen_path:
        coverage = "none"                                  # no generation-path outputs -> nothing to check
    elif flagged == len(gen_path):
        coverage = "all"
    elif flagged == 0:
        coverage = "none"
    else:
        coverage = "partial"
    provisional = coverage == "partial"

    comparable = fresh_global["comparable_fields"]
    accepted = fresh_global["counts"]["accepted_unchanged"]
    rate = round(accepted / comparable, 6) if comparable else 0.0

    recs_by_field = {}
    for r in fresh:
        recs_by_field.setdefault(r.get("field"), []).append(r)
    total_edited = sum(1 for r in fresh if r.get("category") in _EDIT_CATEGORIES)
    per_field = {}
    for f in fields:
        frs = recs_by_field.get(f, [])
        cf = len(frs)
        acc = sum(1 for r in frs if r.get("category") == "accepted_unchanged")
        edited = sum(1 for r in frs if r.get("category") in _EDIT_CATEGORIES)
        effort, method = _field_effort(frs)
        per_field[f] = {
            "comparable_fields": cf, "accepted": acc,
            "acceptance_rate": round(acc / cf, 6) if cf else 0.0,
            "edited": edited,
            "edit_share": round(edited / total_edited, 6) if total_edited else 0.0,
            "edit_effort": effort, "effort_method": method,
        }
    burden = sorted(({"field": f, **v} for f, v in per_field.items()),
                    key=lambda x: (-x["edited"], -x["edit_effort"], x["field"]))
    return {
        "version": METADATA_ACCURACY_VERSION,
        "acceptance": {"numerator": accepted, "denominator": comparable, "rate": rate},
        "target_low": METADATA_ACCURACY_TARGET_LOW, "target_high": METADATA_ACCURACY_TARGET_HIGH,
        # Withheld (None) when coverage is partial (split untrustworthy) OR nothing was freshly generated
        # (empty denominator — "0% accepted" would misread as an LLM failure).
        "meets_target": (None if (provisional or comparable == 0)
                         else rate >= METADATA_ACCURACY_TARGET_LOW),
        "provisional": provisional,
        "comparable_fields": comparable,
        "total_edited_fields": total_edited,
        "per_field": per_field,
        "editorial_burden": burden,   # ranked: where the publisher's editing work concentrates
        # v3: denominator = fields an LLM produced THIS revision (origin-aware; = fresh-only on first pubs).
        "denominator_basis": "llm_generated_this_revision_only",
        "excluded_preserved_field_count": len(excluded),
        "excluded_preserved_artifacts": sorted({r.get("artifact_id") for r in excluded}),
        "disposition_coverage": coverage,   # none (legacy) | all (contract-conformant) | partial (violation)
        # Low-confidence marker (advisory only — does NOT change meets_target): a rate of exactly 1.0 with
        # zero edits over a non-empty denominator is the "approved without per-artifact inspection" pattern
        # (bulk Approve-All), i.e. not evidence of LLM quality. Interim signal until the Publisher emits a
        # dedicated bulk-approve flag (post-Week-12 Gate C).
        "low_confidence_no_inspection": bool(comparable > 0 and rate == 1.0 and total_edited == 0),
        # Fresh-only descriptive aggregate — the headline sources every rate from here (never from the
        # all-common `global`), so the report can't carry two acceptance numbers on two denominators.
        "aggregate": fresh_global,
    }


def compute_metadata_benchmark(canonical_review):
    """Deterministic metadata revision-distance benchmark for one canonical review.

    Returns global + per-field aggregates (numerators/denominators preserved), one auditable record
    per (artifact, field) with category + distance + measures + content hashes (NO raw text), and the
    version/thresholds/weights used. Manual publications are NOT-APPLICABLE.
    """
    if canonical_review.get("applicability") == APPLICABILITY_MANUAL:
        return {"applicable": False, "reason": "manual_publication",
                "version": METADATA_REVISION_DISTANCE_VERSION}

    generated = canonical_review["generated"]["metadata"]
    approved = canonical_review["approved"]["metadata"]
    common = sorted(set(generated) & set(approved))
    generated_only = sorted(set(generated) - set(approved))   # artifact removed at approval
    approved_only = sorted(set(approved) - set(generated))    # artifact added at approval

    # v1.1 four | v2 per-leaf set (the editorial leaves the adapter extracted). Fall back to the v1.1
    # skeleton when nothing was extracted (empty generated metadata) so the per-field shape is stable.
    fields = _field_list(generated) or list(FIELDS)

    g_tally, distances, weighted_sum = _empty_tally(), [], 0.0
    gen_pop = app_pop = 0
    per_field = {f: {"tally": _empty_tally(), "distances": [], "weighted": 0.0,
                     "gen_pop": 0, "app_pop": 0} for f in fields}
    records = []
    comparable_artifacts = 0
    # Non-editorial fields (computed/publisher, e.g. colors, publisher_notes) are recorded as HASHES only
    # for auditability and EXCLUDED from every editorial tally/denominator. Never raw text.
    non_editorial = {}
    generation_counts = {}   # per-artifact recall count (best-effort; present only when the Publisher emits it)

    for aid in common:
        g, a = generated[aid], approved[aid]
        schema_match = g.get("schema_version") == a.get("schema_version")
        if schema_match:
            comparable_artifacts += 1
        # Record non-editorial fields from BOTH sides (colors is computed on both; publisher_notes is
        # authored at approval, so it appears on the approved side). Hash only — never raw text.
        g_ne, a_ne = g.get("non_editorial") or {}, a.get("non_editorial") or {}
        if g_ne or a_ne:
            non_editorial[aid] = {leaf: {"generated": _sha256(g_ne.get(leaf)) if leaf in g_ne else None,
                                         "approved": _sha256(a_ne.get(leaf)) if leaf in a_ne else None}
                                  for leaf in sorted(set(g_ne) | set(a_ne))}
        if g.get("generation_count") is not None:
            generation_counts[aid] = g.get("generation_count")
        gf, af = g.get("fields") or {}, a.get("fields") or {}
        for field in fields:
            # A leaf marker-excluded (routed to non_editorial) on EITHER side for this artifact is not an
            # editorial comparison for it — skip, so inconsistent per-panel `field_sources` can never
            # fabricate a phantom added/removed/abstention record. (Skew is handled below over the whole set.)
            if schema_match and not (field in gf and field in af):
                continue
            gv, av = gf.get(field), af.get(field)
            if not schema_match:
                category, dist, measures = "unsupported_schema", None, None
            else:
                category, dist, measures = _classify(gv, av)
            g_tally[category] += 1
            per_field[field]["tally"][category] += 1
            if not _is_empty(gv):
                gen_pop += 1
                per_field[field]["gen_pop"] += 1
            if not _is_empty(av):
                app_pop += 1
                per_field[field]["app_pop"] += 1
            if category in WEIGHTS:
                weighted_sum += WEIGHTS[category]
                per_field[field]["weighted"] += WEIGHTS[category]
            if dist is not None:
                distances.append(dist)
                per_field[field]["distances"].append(dist)
            records.append({
                "artifact_id": aid, "field": field, "category": category, "distance": dist,
                "generated_sha256": _sha256(gv), "approved_sha256": _sha256(av),
                "generated_empty": _is_empty(gv), "approved_empty": _is_empty(av),
                # Publisher-emitted per-output disposition (fresh|preserved_*); None on legacy revisions.
                # v3 revision provenance: `origin` (present ONLY on the revision-inheritance path — its
                # presence discriminates) drives `_counts_toward_acceptance`. Absent -> v2 fresh-only filter.
                "generated_disposition": g.get("generation_disposition"),
                "generated_origin": g.get("origin"),
                "generated_has_origin": bool(g.get("has_origin")),
                "measures": measures,
            })

    per_field_all_common = {f: _aggregate(pf["tally"], pf["distances"], pf["weighted"],
                                          pf["gen_pop"], pf["app_pop"], comparable_artifacts)
                            for f, pf in per_field.items()}
    global_all_common = _aggregate(g_tally, distances, weighted_sum, gen_pop, app_pop, comparable_artifacts)

    # Fresh-only aggregates — the CERTIFIED surface (preserved outputs excluded). Absent disposition
    # counts as fresh (legacy backward-compat), so on all-fresh data these equal the all-common blocks.
    # These are what `global`/`per_field` expose so every downstream consumer (report body, index entry,
    # Metadata Intelligence trend) reads the fresh-only number, never the preserved-inflated one.
    _fresh = _counts_toward_acceptance   # v3: revision-aware surface (same predicate as the acceptance headline)
    fresh_records = [r for r in records if _fresh(r)]
    # Fresh SCHEMA-MATCHED artifacts (category != unsupported_schema) — mirrors comparable_artifacts, so
    # corrections_per_artifact uses the same artifact-count basis on all-fresh data.
    fresh_comparable_artifacts = len({r["artifact_id"] for r in fresh_records
                                      if r["category"] != "unsupported_schema"})
    fresh_global = _aggregate_records(fresh_records, fresh_comparable_artifacts)
    fresh_per_field_out = {f: _aggregate_records([r for r in fresh_records if r["field"] == f],
                                                 fresh_comparable_artifacts) for f in fields}

    return {
        "applicable": True,
        "version": METADATA_REVISION_DISTANCE_VERSION,
        "field_set_version": ("v2" if str(_schema_version_of(generated)).startswith("v2") else "v1.1"),
        "fields": list(fields),
        "thresholds": {"minor": T_MINOR, "moderate": T_MODERATE, "major": T_MAJOR},
        "weights": dict(WEIGHTS),
        "distance_definition": "normalized char-level Levenshtein over canonical value rendering",
        "artifacts_common": len(common),
        "comparable_artifacts": comparable_artifacts,             # all-common structural fact
        "fresh_comparable_artifacts": fresh_comparable_artifacts,  # matches the fresh `global` sample basis
        "artifact_removed_at_approval": generated_only,
        "artifact_added_at_approval": approved_only,
        # `global` / `per_field` are the CERTIFIED fresh-only surfaces (preserved outputs excluded) that
        # every consumer reads. The all-common revision-distance record (includes preserved, descriptive
        # only) is retained beside them for full auditability.
        "global": fresh_global,
        "per_field": fresh_per_field_out,
        "global_all_common": global_all_common,
        "per_field_all_common": per_field_all_common,
        "metadata_accuracy": _metadata_accuracy(records, fresh_global, fields),
        # Non-editorial fields (computed/publisher) recorded as hashes only, excluded from every metric.
        "non_editorial": non_editorial,
        # "LLM calls per panel" from the per-panel recall counter — best-effort (None until the Publisher
        # emits generation_count with the recall endpoint).
        "llm_calls_per_panel": (_calls_metric(generation_counts) if generation_counts else None),
        "records": records,   # references + hashes only — never raw generated/approved text
    }


def benchmark_headline(benchmark):
    """The compact per-report metadata metrics the index entry carries for search/graphs (pure).

    v2: EVERY rate below is sourced from the fresh-only aggregate (``metadata_accuracy.aggregate``), the
    same denominator as the acceptance headline — so the report never carries two acceptance numbers on
    two denominators. The all-common ``global`` block stays in the full report as a descriptive record but
    is deliberately NOT surfaced here. Falls back to ``global`` only if the fresh aggregate is absent
    (defensive; should not happen for an applicable benchmark)."""
    if not benchmark.get("applicable"):
        return {"applicable": False, "reason": benchmark.get("reason")}
    ma = benchmark.get("metadata_accuracy") or {}
    g = ma.get("aggregate") or benchmark["global"]   # fresh-only surface
    return {
        "applicable": True,
        # Metadata Headline Accuracy v2 — the field acceptance rate (the "few edits" number), fresh-only.
        "metadata_accuracy_version": ma.get("version"),
        "metadata_accuracy": (ma.get("acceptance") or {}).get("rate"),
        "metadata_accuracy_meets_target": ma.get("meets_target"),
        "metadata_accuracy_provisional": ma.get("provisional"),
        # Advisory: rate 1.0 with zero edits — likely bulk-approved without per-artifact inspection.
        # Surfaced here so the compact headline the dashboard reads can qualify the number (never gates).
        "low_confidence_no_inspection": ma.get("low_confidence_no_inspection"),
        "disposition_coverage": ma.get("disposition_coverage"),
        "denominator_basis": ma.get("denominator_basis"),
        "excluded_preserved_field_count": ma.get("excluded_preserved_field_count"),
        "comparable_fields": g["comparable_fields"],
        "fields_generated": g["fields_generated"],
        "fields_approved": g["fields_approved"],
        "accepted_unchanged_rate": g["accepted_unchanged_rate"]["rate"],
        "minor_wording_edit_rate": g["minor_wording_edit_rate"]["rate"],
        "moderate_rewrite_rate": g["moderate_rewrite_rate"]["rate"],
        "major_rewrite_rate": g["major_rewrite_rate"]["rate"],
        "complete_replacement_rate": g["complete_replacement_rate"]["rate"],
        "unchanged_metadata_rate": g["unchanged_metadata_rate"]["rate"],
        "average_revision_distance": g["average_revision_distance"],
        "median_revision_distance": g["median_revision_distance"],
        "weighted_editorial_intervention_score": g["weighted_editorial_intervention_score"]["score"],
        "corrections_per_artifact": g["corrections_per_artifact"]["rate"],
    }
