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

METADATA_REVISION_DISTANCE_VERSION = "v1"  # PROVISIONAL — thresholds/weights subject to review

# The four canonical content fields the adapter extracts (identity space is shared both sides).
FIELDS = ("classification.tags", "entities.characters", "narrative.dialogue", "narrative.summary")

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
    if d == 0.0 or m["structural_equal"]:
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
        "average_revision_distance": round(statistics.fmean(distances), 6) if distances else 0.0,
        "median_revision_distance": round(statistics.median(distances), 6) if distances else 0.0,
        "corrections_per_artifact": _ratio(edits, artifacts),
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

    g_tally, distances, weighted_sum = _empty_tally(), [], 0.0
    gen_pop = app_pop = 0
    per_field = {f: {"tally": _empty_tally(), "distances": [], "weighted": 0.0,
                     "gen_pop": 0, "app_pop": 0} for f in FIELDS}
    records = []
    comparable_artifacts = 0

    for aid in common:
        g, a = generated[aid], approved[aid]
        schema_match = g.get("schema_version") == a.get("schema_version")
        if schema_match:
            comparable_artifacts += 1
        for field in FIELDS:
            gv, av = g["fields"].get(field), a["fields"].get(field)
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
                "measures": measures,
            })

    per_field_out = {f: _aggregate(pf["tally"], pf["distances"], pf["weighted"],
                                   pf["gen_pop"], pf["app_pop"], comparable_artifacts)
                     for f, pf in per_field.items()}

    return {
        "applicable": True,
        "version": METADATA_REVISION_DISTANCE_VERSION,
        "thresholds": {"minor": T_MINOR, "moderate": T_MODERATE, "major": T_MAJOR},
        "weights": dict(WEIGHTS),
        "distance_definition": "normalized char-level Levenshtein over canonical value rendering",
        "artifacts_common": len(common),
        "comparable_artifacts": comparable_artifacts,
        "artifact_removed_at_approval": generated_only,
        "artifact_added_at_approval": approved_only,
        "global": _aggregate(g_tally, distances, weighted_sum, gen_pop, app_pop, comparable_artifacts),
        "per_field": per_field_out,
        "records": records,   # references + hashes only — never raw generated/approved text
    }


def benchmark_headline(benchmark):
    """The compact per-report metadata metrics the index entry carries for search/graphs (pure)."""
    if not benchmark.get("applicable"):
        return {"applicable": False, "reason": benchmark.get("reason")}
    g = benchmark["global"]
    return {
        "applicable": True,
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
