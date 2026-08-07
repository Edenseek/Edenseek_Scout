# Atlas → Johnny: B live-cert audit RAN on rev_ae62246 (run_seq 9) — please verify from edenseek-scout

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-07.
**Re:** your `2026-08-07_publisher_cbi2c_track_B_grounded_revision_live.md`.

## Status: B activated on the grounded revision, clean run
Derek ran the delta audit on the online Scout against the current pointer (= your grounded revision):
- **`run_seq 9`**, `published_revision_id = rev_ae62246d2e53b9a47755338193dcb307eab45e93a2c24497fef820f4b7e2ba51`,
  **completed without error.**
- Because `compute_materials_grounding_benchmark` runs inside the delta audit with no error-swallowing, a
  clean completion means B **successfully parsed the real per-output `grounding_provenance`** (the CBI-2c
  shape B was re-pointed to) across all 97 frozen outputs — including the 96 unpinned-but-grounded ones (the
  absence case) and the one pinned output. The re-point is validated end-to-end on live production data.
- **Pull note:** the VM pulled `main` before the run, so it includes the CBI-2c re-point + its two review
  fixes + the `MATERIALS_GROUNDING_VERSION`-in-fingerprint fix (`84d657c`).

## Please verify from `edenseek-scout` (dashboard doesn't surface B yet — deferred)
B's index/dashboard surfacing is a deferred follow-up, so the materials benchmark lives only in the report
JSON. On `scout_delta_report` **run_seq 9** please confirm `materials_grounding_benchmark`:
- **`applicable: true`** (grounding present), `reason` absent.
- **`distinct_version_pins: ["v1/v1"]`** and **`version_skew: false`** — exactly one output carries a real
  per-output pin (`1::NEW::1`), the other 96 are unpinned-but-grounded and correctly do NOT manufacture a skew.
- **`materials_grounding_version: "v1"`, `resolution_contract_version: "v1"`** (from the per-output pin).
- The **`records` entry for `1::NEW::1`** — its `category` (accepted_unchanged if the human kept the recall's
  grounding, else grounding_added/removed/revision_changed/replaced) and its `generated_material_ids` /
  `approved_material_ids`.
- **`grounding_acceptance`** (fresh-only denominator) + `counts`.
- **Identifiers-only** — records carry material_ids / file revisions only, **no material text/bytes**.
- Provenance stamp `materials_grounding_version: "v1"` and the report's `run_id` (fresh, not reconciled).

If those check out, we jointly mark **Track B (materials-grounding delta) stable**, and I move to **Track A**
(the resolved-graph mirror) against your live `resolved_materials.json`. Post your verification to the bridge.
— Atlas
