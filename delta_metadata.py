"""Deterministic generated-vs-approved METADATA delta (Scout 6.3, Phase A).

Pure functions over Scout's canonical metadata model (produced by
``review_contract_adapter``). Implements the Stage-3(automated)-vs-Stage-4(approved) metadata
metrics of ``SCOUT_APPROVAL_DELTA_ARCHITECTURE.md``, field-by-field per artifact:
acceptance / edit / addition / deletion / hallucination-proxy / completeness. No LLM/vision —
the hallucination metric is an explicit deterministic PROXY (a remove/replace signature), not
a ground-truth verdict.

Comparability (per the architecture): metadata is compared only within a single metadata
schema version; artifacts whose generated/approved schema versions differ are reported as
``schema_version_mismatch`` and excluded from the field aggregates (never silently mixed).
Artifact correspondence is by ``artifact_id`` (the identity space the adapter guarantees:
generated ``panel_key`` == approved ``artifact_id``); geometry split/merge that renamed ids is
surfaced by the geometry delta.
"""
from review_contract_adapter import APPLICABILITY_MANUAL


def _is_empty(v):
    return v is None or v == "" or v == [] or v == {}


def _classify_fields(gen_fields, app_fields):
    """Per-artifact field tallies from the generated→approved diff."""
    names = sorted(set(gen_fields) | set(app_fields))
    gen_populated = accepted = edited = deleted = added = app_populated = 0
    for name in names:
        g, a = gen_fields.get(name), app_fields.get(name)
        g_empty, a_empty = _is_empty(g), _is_empty(a)
        if not g_empty:
            gen_populated += 1
        if not a_empty:
            app_populated += 1
        if not g_empty and not a_empty:
            accepted += 1 if g == a else 0
            edited += 0 if g == a else 1
        elif not g_empty and a_empty:
            deleted += 1                # automated had it; approval removed it
        elif g_empty and not a_empty:
            added += 1                  # approval populated what automation left empty
    return {
        "expected": len(names), "gen_populated": gen_populated, "app_populated": app_populated,
        "accepted": accepted, "edited": edited, "deleted": deleted, "added": added,
    }


def _rate(numer, denom):
    return round(numer / denom, 6) if denom else 0.0


def compute_metadata_delta(canonical_review):
    """Metadata delta for one canonical review. Manual publications are NOT-APPLICABLE."""
    if canonical_review.get("applicability") == APPLICABILITY_MANUAL:
        return {"applicable": False, "reason": "manual_publication",
                "note": "manual publication has no generated side; metadata delta is not applicable"}

    generated = canonical_review["generated"]["metadata"]
    approved = canonical_review["approved"]["metadata"]
    gen_ids, app_ids = set(generated), set(approved)

    generated_only = sorted(gen_ids - app_ids)   # artifact-level deletions
    approved_only = sorted(app_ids - gen_ids)     # artifact-level additions
    common = sorted(gen_ids & app_ids)

    compared, schema_mismatch = [], []
    for aid in common:
        if generated[aid].get("schema_version") == approved[aid].get("schema_version"):
            compared.append(aid)
        else:
            schema_mismatch.append(aid)

    agg = {"expected": 0, "gen_populated": 0, "app_populated": 0,
           "accepted": 0, "edited": 0, "deleted": 0, "added": 0}
    per_artifact = {}
    for aid in compared:
        t = _classify_fields(generated[aid]["fields"], approved[aid]["fields"])
        per_artifact[aid] = t
        for k in agg:
            agg[k] += t[k]

    gen_pop, app_pop, expected = agg["gen_populated"], agg["app_populated"], agg["expected"]
    return {
        "applicable": True,
        "compared_artifact_count": len(compared),
        "generated_only_artifact_ids": generated_only,   # present in automation, absent at approval
        "approved_only_artifact_ids": approved_only,      # new at approval
        "schema_version_mismatch_artifact_ids": schema_mismatch,
        "acceptance_rate": _rate(agg["accepted"], gen_pop),
        "edit_rate": _rate(agg["edited"], gen_pop),
        "deletion_rate": _rate(agg["deleted"], gen_pop),
        "addition_rate": _rate(agg["added"], app_pop),
        "hallucination_proxy_rate": _rate(agg["edited"] + agg["deleted"], gen_pop),  # remove/replace signature
        "completeness": _rate(app_pop, expected),
        "totals": agg,
        "per_artifact": per_artifact,
    }
