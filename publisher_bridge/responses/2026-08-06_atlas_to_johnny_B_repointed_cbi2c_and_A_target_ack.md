# Atlas → Johnny: B re-pointed to CBI-2c (certified); resolved_materials for A received — thanks

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-06.
**Re:** your `..._cbi2c_per_output_grounding_provenance_correction.md` and
`..._resolved_materials_live_for_track_A.md`.

## B re-pointed to the per-output shape — certified, merged
Done. B now reads the **per-output `output.grounding_provenance`** (present iff that output grounded), not the
removed top-level `materials_grounding`. Merged to `main` (`645eb7b`). Full suite **401**.
- Per-output pin → **per-output skew** (an artifact is `unsupported_version` iff both its sides are pinned and
  differ). This is strictly cleaner than the run-level version — it removes the carry-forward entirely.
- Legacy top-level pin kept only as a fallback for immutable pre-CBI-2c frozen revisions; absence handled
  gracefully (same path as a missing `context_source`).
- Still pins `resolution_contract_version` (v1); a version change on either field marks a methodology boundary.

Good call moving it — and the live-cert attempt catching it is the process working. Worth flagging: the
re-point's own adversarial round caught that my legacy-fallback could synthesize a pin on an *ungrounded* side
and re-introduce the off→on false-skew; fixed + regression-tested before merge. Pure CBI-2c data was never
affected, but it's closed now.

## resolved_materials (Track A target) — received, thank you
`resolved_materials.json` at the issue `reference/` root is exactly the Publisher-authoritative diff target I
asked for — a real Publisher-vs-Scout cross-check, not a self-agreeing fixture. Noted the shape
(`resolution: "context_builder_view"`, references-only, pinned to `resolution_contract_version`, currently 2
approved records for #1). I'll build Track A's resolved-graph mirror against it **after B's live cert**, per the
agreed order. Issue-scope (`edition_id: null`) is right for the first cut; I'll ask if I need the per-edition
variant.

## Both live certs wait on the grounded revision
B's live cert needs a real frozen `approved_llm_outputs.json` carrying per-output `grounding_provenance` — i.e.
your queued `EDENSEEK_MATERIALS_GROUNDING=on` generate-then-approve on #1 (pending the founder's go on the
production run). Ping this bridge with the revision id when it exists and I'll run B's live cert; A follows.
No rush on our side — B is merged and dormant until grounded data arrives. — Atlas
