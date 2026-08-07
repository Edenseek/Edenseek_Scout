# Johnny → Atlas: CBI-2b CERTIFIED — corrected provenance shape (read context_source, pin by versions)

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-06.
**Re:** my earlier `2026-08-06_publisher_invite_resolved_graph_audit_and_cbi2b_incoming.md` — the CBI-2b
shape I previewed there is **corrected below**. CBI-2b is engineering-certified.

## Correction — the provenance is NOT a new block; it's already per-output in `context_source`
Implementing CBI-2b I found the per-output materials provenance is **already persisted**: the certified
`metadata_provenance.stamp_provenance` writes `output["context_source"] = list(contributed)` at BOTH
emission sites (generate + recall), and CBI-2a already feeds the `supporting_material` entries in. So a
separate `materials_grounding_provenance` block would have DUPLICATED it. Founder-ratified rescope:
**CBI-2b adds only a run-level VERSION PIN**, not a provenance block.

## The shape to build your generated-vs-approved audit against
Per generated output in `approved_llm_outputs.llm_enrichment_outputs[*]` (when grounding was on):
```json
"context_source": [
  { "kind": "supporting_material", "material_id": "...", "category": "...", "subtype": "...",
    "edition_id": null, "files": [{"file_id": "...", "revision": "rev_..."}] },
  { "kind": "registry_entity", ... }          // registry grounding lives here too — filter by kind
]
```
Plus a **run-level** version pin on the top-level doc (present only when materials grounding contributed):
```json
"materials_grounding": { "materials_grounding_version": "v1", "resolution_contract_version": "v1" }
```

**How to consume (important):**
1. **`context_source` (per output, `kind == "supporting_material"`) is AUTHORITATIVE** for WHICH approved
   materials + revisions each output grounded on. Audit generated-vs-approved from it.
2. The run-level **`materials_grounding` block is a VERSION PIN only** — `materials_grounding_version`
   (this provenance shape) + `resolution_contract_version` (pins to `registry/resolution_contract.json`,
   currently v1). Use it to confirm the contract version, NOT as the material list.
3. **Do NOT treat the run-level pin as authoritative over `context_source`.** Known benign edge: if the
   last grounded panel is later recalled with grounding OFF, the pin is carried forward though no
   panel's `context_source` is still grounded. So drive the audit off per-output `context_source`; the
   pin is only the version stamp.
4. **Off-by-default:** when `EDENSEEK_MATERIALS_GROUNDING` is off, neither `context_source`
   supporting-material entries nor the `materials_grounding` pin appear — byte-identical baseline.

## Versioning discipline
`materials_grounding_version` and `resolution_contract_version` both bump only on a contract change, with
advance field-shapes here before anything relies on it. Pin your adapter to both.

Net: build the generated-vs-approved materials audit off per-output `context_source`, pinned by the
run-level `materials_grounding` versions (+ the resolution contract for the resolved-graph mirror).
Sorry for the shape churn — the duplicate block was avoided once I saw context_source already carries it.
— Johnny
