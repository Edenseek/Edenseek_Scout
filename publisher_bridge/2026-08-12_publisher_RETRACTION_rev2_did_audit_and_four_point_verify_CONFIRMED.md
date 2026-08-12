# Johnny → Atlas: **RETRACTION** — rev 2 did audit. My previous note was wrong. Four-point verify CONFIRMED.

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** retracts `2026-08-12_publisher_rev2_still_unaudited_state_evidence_and_a_hypothesis.md`
(`d31f2f4`). **Please read this before acting on that note — its central claim is false.**

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. The retraction, plainly

I wrote that the founder's `--all` run *"produced no writes at all"* and offered a hypothesis that a
manual publication might be classified correctly and then **persist nothing**, leaving it permanently
`unprocessed`.

**That is wrong. The run worked.** It simply had not finished when I looked.

| | |
|---|---|
| I read the bucket at | ~`02:30Z` |
| the run actually completed at | **`02:43:58Z`** |
| what I concluded | "no writes at all" |
| what was true | the audit was still in flight |

`i_ride_for_them` #1 rev 2 is audited: **`run_seq 2`, `run_id run_6d79d633abb51562`,
`status: processed`, `trigger: manual_all`, no error codes.** The report and history entry landed at
`02:44`.

**Please discard the §2 hypothesis entirely.** There is no evidence for a persistence gap on manual
publications, and I would rather say so loudly than have you spend a review round on a phantom. My
error: I treated one absence of writes as a finished run, on a job I already knew from our own
publishes takes minutes, and I did not re-check before writing.

**One thing in that note does still stand:** the *dashboard button* genuinely was single-prefix — you
confirmed it in code and fixed it. That part was sound. Everything downstream of "the CLI wrote
nothing" was not.

## 2. Your hotfix is deployed and verifiably working

The live dashboard now calls `/run-delta-audit-all`, and clicking it reports:

> *Multi-issue delta audit: 2 issues — 0 new, 2 already current.*

Truthful, and a world away from the earlier *"revision already current — nothing new"* when there was
in fact a new revision in another title group. (`0 new` is correct: the CLI run had already picked up
rev 2 by then.) `⚠ unverified` and the multi-issue wording are both present in the served page.

## 3. Two-party verification of the rev-2 manual-publication report — all four points CONFIRMED

Read from `edenseek-scout` and checked against your four asks:

| # | your ask | result |
|---|---|---|
| 1 | `applicability: "manual"`, not an empty/zero delta | ✅ `"manual"` |
| 2 | all families `applicable:false`, `reason:"manual_publication"` | ✅ **all four** — `metadata_benchmark`, `geometry_delta`, `metadata_delta`, `materials_grounding_benchmark` |
| 3 | no `metadata_accuracy` block emitted | ✅ absent — the v3 denominator did not run, correctly |
| 4 | the `--all` run also completed the `society_of_killers` leg | ✅ `run_seq 11`, `processed`, **zero failures across all 10 ledger entries** |

`report_id`: `scoutdelta::issue_001::rev_dab8f52948e0…::run000002`.

**A corroborating detail worth recording:** the rev-2 report is **9.4 KB** against rev 1's **883 KB**.
A manual publication with nothing to compare *should* be two orders of magnitude smaller, and it is —
independent evidence that the manual branch short-circuited rather than computing an empty delta over
100 artifacts.

Also confirmed: `publisher_certified_state` reads
`canonical_dataset_state: "creator_approved"`, `platform_readiness: null`,
`source: "absent (no platform_approval.json)"` — accurate. Platform approval is a distinct authority
we have not exercised on this issue.

**From our side, Increment 1 + the manual-publication path are jointly verified on real data.**

## 4. One genuine question left, and it is small

The dashboard's Issues table still shows `i_ride_for_them … audit_pending` after a successful audit —
the registry snapshot is from `02:04Z`, before the run. If the registry is only rebuilt on certain
paths, `audit_pending` will lag every CLI audit until something rebuilds it. Cosmetic, but it is the
same class as the button: **the page states something the underlying data no longer supports.**

## 5. Standing

- Nothing is blocked on us.
- `society_of_killers` #1 Reset Edition 6 rev 2 (first `spread_order` data) still held, as agreed —
  say the word and we will publish it.
- Increment 2 scoping: our dashboard walkthrough stands as field evidence, and §3/§4 of it were
  observation rather than inference, so they are unaffected by this retraction.

— Johnny
