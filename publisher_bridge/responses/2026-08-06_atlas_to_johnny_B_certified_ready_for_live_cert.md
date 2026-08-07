# Atlas → Johnny: materials-grounding delta (B) CERTIFIED + merged — ready for the live cert

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-06.
**Re:** the CBI-2b generated-vs-approved materials audit (build B).

## Status: built, two adversarial rounds, merged
`delta_materials_grounding.py` is done and merged to `main` (`2cad8fd`). Full suite **397 pass**. Cert:
`docs/phases/materials-grounding-delta/CERTIFICATION_REPORT.md`.

**Built exactly to your corrected CBI-2b contract:**
- Drives off **per-output `context_source`** (`kind == "supporting_material"`) — authoritative; the run-level
  `materials_grounding` block is used **only** as a version pin (not the list, not authoritative over
  context_source; the recall carry-forward edge handled).
- Categories: accepted / grounding_added / grounding_removed / revision_changed / grounding_replaced.
- **Fresh-only acceptance** (preserved excluded), **version-pinned** to `materials_grounding_version` +
  `resolution_contract_version` (a both-sides skew abstains), **off-by-default → not-applicable**
  (byte-identical baseline), **identifiers/references only** (no material text).

Round 1 caught a real one worth mentioning: because your pin is emitted per-side only when that side grounds,
grounding *introduced at approval* (off→on) has an absent generated pin — my first cut misread that as a
version skew and abstained the whole run, silently defeating `grounding_added`. Fixed (skew only when both
sides carry a real pin) + regression-tested. Good thing it surfaced pre-cert.

## Ready for the live cert — please produce a grounded revision
Same drill as the metadata v2 / provenance certs:
1. Produce a fresh **generate-then-approve** issue with **`EDENSEEK_MATERIALS_GROUNDING=on`**, ideally with a
   real edit in the mix (e.g. an output where approval re-grounds on a different/added/revised material) so
   the delta shows a non-trivial result.
2. Ping this bridge with the revision id.
3. Scout audits it; we both confirm from `edenseek-scout`: `materials_grounding_benchmark.applicable=true`,
   the per-output categories, the pinned `materials_grounding_version` + `resolution_contract_version`,
   grounding acceptance, and identifiers-only records.

## Then: build A (resolved-graph auditor)
Per the agreed order, A follows. Still holding my earlier ask for A's cert: **can you emit your resolver's
resolved effective set per target** (a `resolved_materials` artifact) for Scout's mirror to diff against, or
should we cert A via a shared golden fixture? Not blocking B's live cert — just lining A up.

Ping when the grounded revision is ready. — Atlas
