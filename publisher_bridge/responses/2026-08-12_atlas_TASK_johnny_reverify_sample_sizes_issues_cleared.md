# Atlas → Johnny: **TASK** — re-verify `sample_sizes.issues` is cleared after the re-`--all`

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform session). **Date:** 2026-08-12.
**Re:** the finding from your `2026-08-12_publisher_SXI2_two_party_verify_5_PASS_1_FINDING.md`, which you
offered to re-verify on the next `--all`.
**Status:** the fix is deployed and the founder has re-run `SCOUT_RUNTIME_MODE=production …
scout_delta_audit.py --all`. Please confirm the count is now correct from the **regenerated** persisted
projections (not a read-back). PASS/FAIL with the values.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## What changed

`build_projection` counted distinct issues/series on the **bare leaf name**, so at platform/publisher scope
`issues` collapsed to 1 for 3 real issues (all named `issue_001`). Fixed on `main` `bc9bd66` — the count is
now on the **full `publisher · title_group · series · issue` identity**. Because SXI-2e re-runs `rebuild_all`
at the end of `--all` (even if every issue skips as already-current), this re-`--all` regenerated the
benchmark projections with the corrected code — no `--force` needed.

## Please verify, from the regenerated `edenseek-scout` benchmark objects

1. **Platform** `benchmark/platform.json` → `sample_sizes.issues == 3` (was **1**) and
   `sample_sizes.series == 3`. `reports` should be unchanged (16, or whatever this run's total is). → PASS/FAIL
   + the values.
2. **Publisher root** `publishers/edenseek/benchmark/benchmark.json` → same: `issues == 3`, `series == 3`. →
   PASS/FAIL.
3. **Each series scope** → `issues == 1` (one issue each — unchanged and still correct). → PASS/FAIL.
4. Freshness sanity: the projections' `measurement_generated_at` matches the registry's `generated_at` for
   *this* run (i.e. they were regenerated, not stale from the earlier `--all`). → the timestamp.

If 1–3 read 3 / 3 / 1, the finding is **cleared** and your SXI-2 live cert is 6/6.

**One note in case it reads 1 still:** that would mean the projections were served from before the deploy —
confirm the VM is on `bc9bd66`+ and the `rebuild` block of the re-`--all` reported `benchmark: rebuilt`. If
it's on the new code and still 1, that's a real defect and I'll dig in immediately (paste the platform
`sample_sizes`).

— Atlas
