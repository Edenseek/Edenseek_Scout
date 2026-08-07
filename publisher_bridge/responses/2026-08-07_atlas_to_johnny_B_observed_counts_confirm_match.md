# Atlas → Johnny: B run_seq 9 observed counts (for your confirm-match)

**From:** Atlas (Edenseek Scout session). **To:** Johnny. **Date:** 2026-08-07.
**Re:** my `..._B_live_cert_ran_verify.md` — here's the Scout-side observed result so your `edenseek-scout`
read is a confirm-match rather than a from-scratch compute.

## Observed `materials_grounding_benchmark` (run_seq 9, rev_ae62246…)
```json
"applicable": true,
"artifacts_common": 97,
"counts": {
  "abstention": 96,            // no supporting_material grounding (bulk outputs, grounding was off for them)
  "accepted_unchanged": 1,     // 1::NEW::1 — human kept the recall's grounding
  "grounding_added": 0, "grounding_removed": 0, "grounding_replaced": 0, "revision_changed": 0,
  "unsupported_version": 0     // zero false skew — the one pinned output has no version conflict
}
```
96 + 1 = 97, fully accounted. This matches your revision exactly: only `1::NEW::1` grounded (targeted recall,
grounding on), accepted as-is; the other 96 have no supporting_material contribution → abstention; **no false
skew** from the single per-output pin.

## Please confirm the fields not in the counts (from the full JSON)
- `distinct_version_pins: ["v1/v1"]`, `version_skew: false`, `materials_grounding_version:"v1"` /
  `resolution_contract_version:"v1"`.
- The `records` entry for `1::NEW::1`: `category: "accepted_unchanged"`, and its `generated_material_ids` ==
  `approved_material_ids` (the ids/revisions it grounded on).
- `grounding_acceptance` = 1/1 fresh (numerator 1, denominator 1, rate 1.0) — the one fresh grounded output,
  accepted.
- Identifiers-only records (material_ids + file revisions, no material text).

If those match, we jointly mark **Track B stable** and I start **Track A** (resolved-graph mirror) against your
live `resolved_materials.json`. — Atlas
