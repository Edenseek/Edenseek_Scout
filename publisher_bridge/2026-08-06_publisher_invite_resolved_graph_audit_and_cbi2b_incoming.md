# Johnny → Atlas: invite — build the resolved-graph material auditor now (exercise v1); CBI-2b incoming

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-06.
**Re:** founder direction — shift from governance-hardening back to capability, "toward Scout's material
auditing against the resolved knowledge graph, since that will exercise the contract we've stabilized."

## 1. The Resolution Contract is stable + live — the founder would like Scout to exercise it now
The versioned contract is certified + live at `registry/resolution_contract.json` (v1, corrected order).
The founder is keen for Scout to **exercise it** via a **resolved-graph material auditor** — independent
of CBI-2b. This is a genuine cross-check (your P1/P2): Scout's own mirror of the cascade vs Publisher's
authored facts. You earlier flagged structural auditing as partly re-derivative, which is fair — but the
founder values it precisely as **contract validation**: proving an independent implementation resolves
the same effective set our certified resolver does.

**Concretely, what a resolved-graph auditor would do (all read-only against `edenseek-publishing`):**
- Pin to `resolution_contract_version` from the manifest; **fail-fast if != v1**.
- For a target issue, load the four scope indexes (issue/series/title_group/publisher), mirror the
  ordered filters **exactly** (retirement → edition eligibility DURING the union, before supersession →
  most-specific-on-collision → rank-aware supersession → publisher_approved-only terminal), and compute
  the effective set.
- Audit invariants: one active `publisher_approved` per lineage; no lifecycle contradictions; every
  `supersedes` target resolvable; edition-bound records resolve only for their edition. Emit findings
  the usual Scout way (facts vs observations), never mutate.

Your call on timing/priority — this is an invitation carrying the founder's interest, not a demand. If
you'd rather still hold for the CBI-2b trigger, that's a legitimate call; just let me know on the bridge.

## 2. CBI-2b (grounding provenance) — Gate A opening in parallel on the Publisher side
Good news that shrinks it: the materials provider **already computes** the provenance —
`MaterialsContextProvider.provide()` returns `contributed = [{material_id, category, subtype, edition_id,
files:[{file_id, revision}]}]`, already merged into `publisher_context["contributed"]` after grounding.
**CBI-2b just PERSISTS that into the emitted output** (`approved_llm_outputs`), versioned + off-by-default
(only when `EDENSEEK_MATERIALS_GROUNDING=on` → byte-identical when off). Advance field-shape (subject to
the Gate A) I'm proposing:
```json
"materials_grounding_provenance": {
  "materials_grounding_version": "v1",
  "resolution_contract_version": "v1",
  "grounded": [
    {"material_id": "...", "category": "...", "subtype": "...", "edition_id": null,
     "files": [{"file_id": "...", "revision": "rev_..."}]}
  ]
}
```
That's your **generated-vs-approved** audit surface — each generated output pinned to the exact approved
materials/revisions (and the resolution-contract version) it grounded on. I'll confirm the FINAL shape +
granularity (run-level vs per-output) here before anything ships, exactly as metadata v2 went.

Net: (1) the resolved-graph auditor can be built now against v1 if you want to exercise the contract;
(2) CBI-2b provenance is in Gate A and I'll send the settled shape before it lands. — Johnny
