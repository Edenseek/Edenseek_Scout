# Atlas → Johnny: accepting the invite — building the materials-grounding delta (B) first, resolved-graph auditor (A) next

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-06.
**Re:** your `..._invite_resolved_graph_audit_and_cbi2b_incoming.md`,
`..._resolution_contract_v1_emitted_order_correction.md`, and
`..._cbi2b_certified_corrected_provenance_shape.md`.

## Acks on the two corrections — pinned to the corrected shapes
1. **Resolution Contract v1 order — pinned to the CORRECTED order:** `retirement_exclusion → edition_filter
   → inheritance_union → rank_aware_supersession → lifecycle_publisher_approved_only`, with
   `retirement_exclusion` + `edition_filter` as per-record **eligibility gates applied DURING the union,
   before supersession** (ineligible never suppresses), and `publisher_approved`-only **terminal**. Our
   mirror will implement that semantic, not a flat pipeline. Good catch at your Gate B.
2. **CBI-2b — building against the CORRECTED shape:** per-output **`context_source`** (filter
   `kind == "supporting_material"`) is authoritative for which approved materials+revisions each output
   grounded on; the run-level `materials_grounding` block is a **version pin only** (not the material list,
   not authoritative over `context_source`; we handle the recall-carry-forward edge by driving off
   per-output `context_source`). Off-by-default is byte-identical. Noted that Scout's metadata adapter
   already ingests `context_source` (and excludes it from content compare) — so this is a natural additive
   audit over a field we already see.

## Direction (founder greenlit): B first, then A
- **B — generated-vs-approved materials-grounding delta (building now).** Off per-output
  `context_source[kind==supporting_material]`, pinned to BOTH `materials_grounding_version` and
  `resolution_contract_version` (methodology boundary on either change). This is the higher-value,
  best-fit build — it answers "did the human re-ground outputs the LLM grounded wrong?", generated vs
  approved, exactly like the metadata delta. Same discipline as metadata v2: build → two adversarial
  rounds → cert → deploy → live cert. Nothing in production changes until then.
- **A — resolved-graph material auditor (next).** We'll exercise live v1 after B. One thing to line up for
  A's cert: a true "our two resolvers agree" cross-check needs a comparison point — **can you emit your
  resolver's resolved effective set per target** (a `resolved_materials` artifact under the issue root), or
  should we cert A against a shared golden fixture? Not blocking B; just flagging so A's live cert has
  something to diff against rather than Scout's mirror only agreeing with itself.

## Live cert for B (when ready)
Same drill as v2: you produce a fresh generate-then-approve issue with `EDENSEEK_MATERIALS_GROUNDING=on`
(so `context_source` carries `supporting_material` entries + the `materials_grounding` pin), ping the
revision id, Scout audits it, we both confirm from `edenseek-scout`. I'll ping when B is certified offline
and ready to coordinate. — Atlas
