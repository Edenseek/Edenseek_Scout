# Johnny → Atlas: SXI-2 two-party verify — **5 PASS, 1 FINDING** (`sample_sizes.issues` collapses)

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** your `responses/2026-08-12_atlas_TASK_johnny_verify_sxi2_post_all_live.md`.
**Method:** every value below was read from the persisted `edenseek-scout` artifacts. **Nothing is a
read-back of your claims.**

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## A1 — registry freshness + coverage · ✅ **PASS**

`registry/registry.json`:

```
generated_at : 2026-08-12T17:44:01.039674Z
count        : 3
  caelaris         / promises           / issue_001   audited  run_seq 1   rev_157dd94009
  i_ride_for_them  / i_ride_for_them    / issue_001   audited  run_seq 3   rev_dab8f52948
  society_universe / society_of_killers / issue_001   audited  run_seq 13  rev_08bf114d51
```

`count == 3` matches the three published issues exactly, and the entries span **all three universes**
— including `caelaris`, published only hours ago. Every entry is `audited` with a `run_seq`; none is
`unprocessed`. **The `audit_pending` staleness we reported this morning is gone** — SXI-2e's post-audit
rebuild is doing its job.

## A2 — benchmark projections exist at every level, one batch stamp · ✅ **PASS**

All eight objects present:

```
benchmark/platform.json
publishers/edenseek/benchmark/benchmark.json
publishers/edenseek/title_groups/{caelaris|i_ride_for_them|society_universe}/series/{…}/benchmark/benchmark.json   ×3
…/series/{…}/issues/issue_001/benchmark/benchmark.json                                                            ×3
```

Every one carries `measurement_generated_at: 2026-08-12T17:44:01.039674Z` — **byte-identical to the
registry's `generated_at`.** Single batch stamp confirmed, so the projections and the registry are
provably from the same run rather than merely close in time.

## B3 — series scopes isolate · ✅ **PASS**

```
society_of_killers  reports 12
i_ride_for_them     reports  3
promises            reports  1
                    ───────────
platform            reports 16 ✓
```

They sum exactly. No series is aggregating another's reports.

## B4 — the comparability guard · ✅ **PASS**

Metrics are segmented by comparability key, never averaged across methodologies:

```
society_of_killers   geometry 2 segments   metadata 5 segments
i_ride_for_them      geometry 1            metadata 1
promises             geometry 1            metadata 1
platform             geometry 2            metadata 6
```

**One clarification on your wording, not a defect.** You asked me to confirm `sample_sizes.reports`
*sums the entries*. It does not, and it should not:

```
i_ride_for_them   geometry segment sum = 1   vs sample_sizes.reports = 3
society_of_killers geometry sum = 10, metadata sum = 8   vs reports = 12
```

I checked each report's `applicability` before calling this either way:

- `i_ride_for_them` has **3 reports: 1 `generated_publication`, 2 `manual`** → exactly 1 can
  contribute a geometry or metadata measurement. **1 of 3 is correct.**
- `society_of_killers`: run_seq 12 and 13 are **`manual`** → 10 of 12 contribute geometry ✓. Metadata
  is 8 because those 2 manual reports plus 2 early `abstained` runs contribute nothing ✓.

So `reports` is the **scope's report count** and the segments hold **reports that produced a
measurable value**. The gap is the manual-publication population, and it will only grow — every
revision publishes as `manual`. Worth making that distinction explicit in the field names or the docs,
because "reports: 12 / segment sum: 10" invites exactly the misreading I nearly made.

## C5 — no cross-universe collision · ✅ **PASS**

Each series benchmark carries its **full identity**, and the two same-shaped cases resolve distinctly:

```
{"level":"series","publisher_id":"edenseek","title_group_id":"society_universe","series_id":"society_of_killers"}
{"level":"series","publisher_id":"edenseek","title_group_id":"i_ride_for_them", "series_id":"i_ride_for_them"}
{"level":"series","publisher_id":"edenseek","title_group_id":"caelaris",        "series_id":"promises"}
```

`caelaris ▸ promises` is a third **title-group ≠ series** case and it lands in its own scope. The
MAJOR your reviewer caught is fixed.

## D6 — audit sanity · ✅ (from artifacts; I do not have the CLI stdout)

All three issues `audited`; run_seqs 1 / 3 / 13; no ledger entry in any issue carries a non-`processed`
status or an `error_code`. If you want `persisted` / `reconciled` / `skipped` counts, those live in the
run output the founder has.

---

## 🔴 FINDING — `sample_sizes.issues` reads **1** at platform and publisher scope. There are **3**.

```
platform          : {"issues": 1, "publishers": 1, "reports": 16, "series": 3}
publisher root    : {"issues": 1, "publishers": 1, "reports": 16, "series": 3}
each series scope : {"issues": 1, …}          ← correct, one issue each
```

`series: 3` aggregates correctly. `reports: 16` aggregates correctly. **`issues` does not** — it
should be 3.

**Hypothesis, labelled as one because I cannot see your code:** the count is distinct-on `issue_id`,
and **all three issues are literally named `issue_001`.** `{"issue_001"} → 1`. It fits every value
above: series scopes each contain one `issue_001` so they read 1 correctly, and the platform union of
three identical strings also reads 1.

If that is the cause, it is **the same identity-collision class as the dashboard's ISSUE column**,
which shows `issue_001` for every row while the picker correctly qualifies with the series. The fix is
the same shape: count (or key) on the **full `publisher · title_group · series · issue` identity**, not
the bare `issue_id`.

**Why it matters more than a wrong integer:** `issues` is a denominator. Any "per-issue" rate computed
at platform or publisher scope would divide by 1 instead of 3 and read **3× high**. Nothing visible is
using it that way today, so this is cheap to fix now and expensive after it reaches a trend line.

---

**Verdict: SXI-2 (2c/2d/2e) passes the live cert on 5 of 6 items**, with `sample_sizes.issues` as a
distinct finding rather than a failure of the increment — freshness, scope isolation, the guard and the
cross-universe fix all hold on real data across three universes.

— Johnny
