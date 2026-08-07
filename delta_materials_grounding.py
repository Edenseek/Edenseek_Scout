"""Deterministic, versioned MATERIALS-GROUNDING benchmark (Scout — CBI-2b generated-vs-approved).

Measures how the human approval changed **which approved Supporting Materials each generated output
grounded on** — the materials analogue of the metadata revision-distance benchmark. For each artifact it
compares the generated side's grounding set (the supporting-material entries in that output's
``context_source``) against the approved side's, per (material_id, revision), and classifies the change.

Governance: Scout stores **identifiers only** (material_id / category / subtype / edition_id / file_id /
revision) — these are *references* to the immutable Publisher materials, never material file bytes or text.
Deterministic; no LLM.

Provenance discipline (mirrors metadata v2):
- **Authoritative source is per-output `context_source`**, never the run-level pin (which carries forward
  across a grounding-off recall). The pin is used ONLY to stamp/boundary the contract versions.
- **Fresh-only acceptance:** a ``preserved_*`` output's grounding equals approved by construction, so it is
  excluded from the acceptance denominator (same as the metadata metric).
- **Version-pinned:** ``materials_grounding_version`` (this benchmark's input contract) +
  ``resolution_contract_version`` (pins the resolution manifest) are comparability axes; a change is a
  methodology boundary. A version SKEW between sides abstains (``unsupported_version``), never a wrong number.
- **Off-by-default is not-applicable, not a failure:** when materials grounding contributed to neither side,
  there is nothing to audit (byte-identical baseline).
"""
from review_contract_adapter import APPLICABILITY_MANUAL

MATERIALS_GROUNDING_VERSION = "v1"


def _ground_key(entry):
    """A hashable identity for one grounded material: (material_id, sorted (file_id,revision) tuples).
    Two outputs ground 'the same way' iff their sets of these keys are equal."""
    files = tuple((f.get("file_id"), f.get("revision")) for f in (entry.get("files") or []))
    return (entry.get("material_id"), files)


def _classify(gen_entries, app_entries):
    """Classify the generated→approved grounding change for one artifact.

    Categories: ``accepted_unchanged`` (identical grounding sets); ``grounding_added`` (approval grounds on
    material(s) the generation didn't); ``grounding_removed`` (approval dropped material(s)); ``revision_changed``
    (same material_id(s), different file revision — the material was revised between generate and approve);
    ``grounding_replaced`` (both added and removed distinct materials). ``abstention`` when neither side grounded.
    """
    g_by_id = {e.get("material_id"): _ground_key(e) for e in gen_entries}
    a_by_id = {e.get("material_id"): _ground_key(e) for e in app_entries}
    if not g_by_id and not a_by_id:
        return "abstention", {}
    g_ids, a_ids = set(g_by_id), set(a_by_id)
    added_ids, removed_ids = a_ids - g_ids, g_ids - a_ids
    common = g_ids & a_ids
    revised_ids = sorted((m for m in common if g_by_id[m] != a_by_id[m]), key=str)
    detail = {"added": sorted(added_ids, key=str), "removed": sorted(removed_ids, key=str),
              "revision_changed": revised_ids}
    if not added_ids and not removed_ids and not revised_ids:
        return "accepted_unchanged", detail
    if added_ids and removed_ids:
        return "grounding_replaced", detail
    if added_ids:
        return "grounding_added", detail
    if removed_ids:
        return "grounding_removed", detail
    return "revision_changed", detail


_EDIT_CATEGORIES = ("grounding_added", "grounding_removed", "revision_changed", "grounding_replaced")


def _pin_versions(pin_side):
    p = pin_side if isinstance(pin_side, dict) else {}
    return (p.get("materials_grounding_version"), p.get("resolution_contract_version"))


def compute_materials_grounding_benchmark(canonical_review):
    """Deterministic materials-grounding benchmark for one canonical review.

    Returns ``{applicable: False, reason}`` for a manual publication or when neither side carries any
    supporting-material grounding (off-by-default baseline). Otherwise a per-artifact record set + a
    fresh-only acceptance headline + the version pins used.
    """
    if canonical_review.get("applicability") == APPLICABILITY_MANUAL:
        return {"applicable": False, "reason": "manual_publication",
                "version": MATERIALS_GROUNDING_VERSION}

    generated = canonical_review["generated"]["metadata"]
    approved = canonical_review["approved"]["metadata"]
    # Legacy (pre-CBI-2c) top-level pin — fallback only for immutable frozen revisions.
    legacy = canonical_review.get("materials_grounding_pin") or {}
    legacy_gen, legacy_app = _pin_versions(legacy.get("generated")), _pin_versions(legacy.get("approved"))

    def _pin_of(entry, legacy_side):
        """The (materials_grounding_version, resolution_contract_version) for one output. CBI-2c: per-output
        ``grounding_provenance``; falls back to the legacy top-level pin for pre-CBI-2c frozen revisions;
        else (None, None) (unpinned — an output that did not ground carries no pin)."""
        gp = entry.get("grounding_provenance")
        if isinstance(gp, dict):
            return _pin_versions(gp)
        return legacy_side

    common = sorted(set(generated) & set(approved))
    # Applicability spans ALL outputs (both sides, every artifact) — grounding introduced on a non-common
    # (added/removed-at-approval) artifact is real grounding activity, so claiming "no_materials_grounding"
    # would be a false baseline. Comparison itself is still generated-vs-approved over COMMON artifacts
    # (a non-common artifact has no counterpart to diff against); those are surfaced separately for transparency.
    def _grounded(m):
        return bool(m.get("grounding"))
    any_grounding = (any(_grounded(o) for o in generated.values())
                     or any(_grounded(o) for o in approved.values()))
    if not any_grounding:
        return {"applicable": False, "reason": "no_materials_grounding",
                "version": MATERIALS_GROUNDING_VERSION}
    grounded_only_generated = sorted(a for a in (set(generated) - set(approved)) if _grounded(generated[a]))
    grounded_only_approved = sorted(a for a in (set(approved) - set(generated)) if _grounded(approved[a]))

    def is_fresh(entry):
        return entry.get("generation_disposition") in (None, "fresh")

    records = []
    tally = {c: 0 for c in ("accepted_unchanged", *_EDIT_CATEGORIES, "abstention", "unsupported_version")}
    fresh_comparable = fresh_accepted = 0
    pins_seen = set()   # distinct per-output pins across grounded outputs (for the report-level summary)
    for aid in common:
        g, a = generated[aid], approved[aid]
        gen_pin, app_pin = _pin_of(g, legacy_gen), _pin_of(a, legacy_app)
        for p in (gen_pin, app_pin):
            if None not in p:
                pins_seen.add(p)
        # PER-OUTPUT version skew: both this output's sides carry a real pin AND they differ. Per-output
        # (CBI-2c) removes the run-level carry-forward — an off->on output has one absent pin -> not a skew.
        if None not in gen_pin and None not in app_pin and gen_pin != app_pin:
            category, detail = "unsupported_version", {}
        else:
            category, detail = _classify(g.get("grounding") or [], a.get("grounding") or [])
        tally[category] += 1
        fresh = is_fresh(g)
        # Fresh-only acceptance denominator: exclude preserved outputs + abstentions + skew.
        if fresh and category not in ("abstention", "unsupported_version"):
            fresh_comparable += 1
            if category == "accepted_unchanged":
                fresh_accepted += 1
        records.append({
            "artifact_id": aid, "category": category,
            # deduped id lists (a material appears at most once per output); str-safe sort.
            "generated_material_ids": sorted({m.get("material_id") for m in (g.get("grounding") or [])},
                                             key=str),
            "approved_material_ids": sorted({m.get("material_id") for m in (a.get("grounding") or [])},
                                            key=str),
            "detail": detail,
            "generated_disposition": g.get("generation_disposition"),
        })

    rate = round(fresh_accepted / fresh_comparable, 6) if fresh_comparable else 0.0
    edited = sum(tally[c] for c in _EDIT_CATEGORIES)
    # Report-level version summary derived from the per-output pins actually seen. Uniform -> the single
    # value; heterogeneous -> None + version_skew (distinct pins coexist across grounded outputs — a real
    # contract-consistency signal, not silently collapsed).
    mg_versions = {p[0] for p in pins_seen}
    rc_versions = {p[1] for p in pins_seen}
    version_skew = tally["unsupported_version"] > 0 or len(pins_seen) > 1
    return {
        "applicable": True,
        "version": MATERIALS_GROUNDING_VERSION,
        "materials_grounding_version": (next(iter(mg_versions)) if len(mg_versions) == 1 else None),
        "resolution_contract_version": (next(iter(rc_versions)) if len(rc_versions) == 1 else None),
        "version_skew": version_skew,
        "distinct_version_pins": sorted(f"{p[0]}/{p[1]}" for p in pins_seen),
        "artifacts_common": len(common),
        # Non-common artifacts that carry grounding — real activity with no generated-vs-approved counterpart
        # to diff; surfaced so they are observed, not silently dropped by the common-only comparison.
        "grounded_only_generated": grounded_only_generated,
        "grounded_only_approved": grounded_only_approved,
        "counts": dict(tally),
        "grounding_acceptance": {"numerator": fresh_accepted, "denominator": fresh_comparable, "rate": rate,
                                 "basis": "fresh_generated_outputs_only"},
        "grounding_edits": edited,
        "records": records,   # identifiers/references only — never material bytes or text
    }

# NOTE: index/search headline + dashboard surfacing for this benchmark are a deferred follow-up
# increment (mirrors how metadata_accuracy's dashboard surfacing was deferred to a joint UI review).
# The benchmark rides on the report body via delta_auditor today; no consumer reads a headline yet.
