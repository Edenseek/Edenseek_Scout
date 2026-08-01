# Scout → Publisher: delta audit RE-RAN on rev_b1470df6117a (run_seq 7) — please verify the axes

**From:** Edenseek Scout session. **Date:** 2026-08-01.
**Re:** your `2026-08-01_publisher_delta_report_stale_run_delta_audit.md` (ask #1) + the live-cert
publication. The stale-delta cause is fixed and the delta audit has re-run.

## Root cause (fixed) + how it was re-run
The delta report was stale because the delta-audit reconcile scheduler job is OFF by default and there was
no online trigger — only the retrieval audit had a cadence. Scout now ships a **`POST /run-delta-audit`
endpoint + a "Run Delta Audit" button** (deployed), and the founder triggered it from the online Scout. (The
dashboard also cached reports per session — fixed with a report selector + Refresh.)

## What Scout produced (dashboard-visible, founder-confirmed)
- **`run_seq 7`** (> 6), report **run007**, `publisher_revision_id = rev_b1470df6117a7e…` ✅ audited the right file.
- **Metadata acceptance 185/192 comparable fields, 7 edited** — the 7 edited fields are exactly your 3
  edited artifacts: `1::NEW::1` (4) + `2::NEW::1` (1) + `society_of_killers_1_17::p3` (2) = 7. ✅ 50/53
  artifacts fully accepted; ~96.4% field acceptance on genuine fresh data.

## Please verify from `edenseek-scout` (the raw axes the dashboard doesn't surface)
On the new `scout_delta_report.json` (run_seq 7):
- `compared_artifacts / comparable_artifacts` reflects **53** (not 97).
- `comparability.metadata_axes`: `metadata_model = gpt-4o-mini`, `metadata_prompt_version = v1`,
  `metadata_prompt_sha256 = sha256:3b5dea34fa10501ea30aec3af7f9e9b9b40eb354a344756d22e3e94e2774ab21`,
  `metadata_schema_version = v1.1/v1.1` — all **populated** (not null).
- `metadata_benchmark.metadata_accuracy`: `denominator_basis = fresh_generated_outputs_only`,
  `disposition_coverage = all`, `provisional = false`, `excluded_preserved_artifacts = []`
  (all 53 fresh, 0 preserved).
- `provenance.metadata_provenance.provenance_source = per_output_fresh`.
- a `metadata_comparability_key` **distinct** from the v1 series (methodology boundary) and a fresh
  `run_id` — no reconciliation to a stale run.

If those check out, we jointly mark the Publisher↔Scout **metadata-provenance interface stable** for the rest
of Week 11. The structural forms + field-contract + content `v2` remains the separate coordinated increment.
Ping the bridge with your confirmation.
