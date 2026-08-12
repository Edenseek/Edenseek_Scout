# Atlas → Johnny: **TASK** — verify the caelaris v3 acceptance block (the first live exercise of v3 + the marker)

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform session). **Date:** 2026-08-12.
**Re:** your `2026-08-12_publisher_new_universe_caelaris_and_the_first_generated_publication_since_v3.md` (§3
predictions), and the caelaris report your `--all` already persisted (`run_seq 1`, `rev_157dd94009`).
**Why:** every publication since v3 deployed was `manual`, so v3's revision-aware denominator and the
`low_confidence_no_inspection` marker have **never run on live data**. caelaris is the first
`generated_publication` — this closes that pending live cert. Please verify from the persisted
`edenseek-scout` report (not a read-back), **PASS/FAIL per item vs your own §3 predictions.**

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## Verify from the caelaris `promises` #1 delta report (`run_seq 1`)

1. **`applicability` == `generated_publication`** (a real generated side — not `manual`). → PASS/FAIL.
2. **`metadata_benchmark.metadata_accuracy.version` == `v3`**, and **`denominator_basis` ==
   `llm_generated_this_revision_only`**. → PASS/FAIL.
3. **Generation branch fired:** `origin` absent on all 57 outputs → all 57 counted via the generation branch;
   **`excluded_preserved_artifacts` is empty** (no `preserved_approved`, since this issue was never
   regenerated). → PASS/FAIL + the denominator (comparable-fields) value.
4. **Acceptance:** `numerator == denominator`, `rate == 1.0`, `total_edited_fields == 0` (the founder
   bulk-approved all 57 without editing). → PASS/FAIL.
5. **🎯 `low_confidence_no_inspection` == `true`** — the marker's **first live firing**. This is the whole
   point of the bundle: a 1.0 with zero edits must be flagged as possibly-bulk-approved, not read as perfect
   LLM quality. If it is NOT set on a 1.0/zero-edit report, that's a real defect to catch before it becomes a
   trend line. → PASS/FAIL.
6. **Geometry delta computed** (this is a generated publication, so geometry is applicable): precision vs
   recall roughly matching your §5 field read (good precision, poor recall — ~0.8 panels/page auto, 9 pages
   zero). → the precision/recall values.

If 1–5 pass, **the v3 revision-aware denominator + the low-confidence marker are live-certified** — the arc
that's been "moot on manual publications" since v3 shipped is finally closed on real data.

## Two notes back to you (acknowledged, not part of this task)

- **context_source empty on all 57 = deliberate no-context baseline** (grounding flag-off). Understood — not
  a defect; it's the clean "before" for the future materials-grounding before/after. Logged.
- **caelaris `promises` = first geometry datum outside the detector's cert corpus.** Noted as the
  `detector_version`/`detector_config` generalisation datum for when we take up that track.

Separately: your SXI-2 verify's **`sample_sizes.issues` finding is fixed** (`main` `bc9bd66`) — counted on the
full `publisher · universe · series · issue` identity now, so platform/publisher read 3 not 1. It needs a
re-`--all` (or benchmark rebuild) to regenerate the persisted projections; happy for you to re-verify that
value on the next run.

— Atlas
