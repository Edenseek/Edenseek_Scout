# Atlas → Johnny: **READY — re-run intake.** Every issue now has a consolidated `scout_report_`.

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform session). **Date:** 2026-08-13.
**Re:** the intake seam — Option A is built, certified, deployed, and the multi-issue `--all` has run.
**Action for you:** re-run `run_intelligence_intake` and confirm `promises` + `i_ride_for_them` now produce
Review Records / Diagnostics. That two-party check is the live cert.

> Bridge ground rule honoured: this file is the only thing written here; no Publisher code touched.

---

## 1. What shipped (merged `5cd6d52`, deployed, `--all` run)

The dataset audit is now multi-issue. `--all` runs the consolidated dataset audit per discovered issue, so
each issue gets a `scout_report_` written under **its own `{issue_prefix}/history/` prefix** — the single hard
requirement you named. Orchestration only: the audit already threads the per-issue context, so `issue_id`,
`provenance.publisher_revision_id`, `provenance.publisher_revision_key` and the write path are all per-issue.
**Same `scout_report_` stem + shape — no intake change on your side.**

Idempotent (an issue whose latest consolidated report already covers its current revision is skipped), folded
into `--all` non-fatally, and single-issue behaviour is byte-identical.

## 2. What to expect when you list the bucket

New consolidated reports should now exist alongside the delta reports:

```
publishers/edenseek/title_groups/caelaris/series/promises/issues/issue_001/history/scout_report_00000N.json
publishers/edenseek/title_groups/society_universe/…/i_ride_for_them/…/issues/issue_001/history/scout_report_00000N.json
```

Each under its own prefix, each carrying its own `issue_id`/revision. So `run_intelligence_intake` should now
find them (`"scout_report_".startswith` matches) and `compose_review_record` should produce a Review Record
per issue → Diagnostics populate for both.

## 3. The verify (two-party, from `edenseek-scout` + your intake)

1. **Reports exist:** each issue has a `…/history/scout_report_*.json` under its OWN prefix. → PASS/FAIL.
2. **Identity is that issue's, not `society_of_killers`:** on `promises`' consolidated report, `issue_id`,
   `provenance.publisher_revision_id` (`rev_892a47be…`) and `publisher_revision_key` resolve to `promises`,
   not the env issue. Likewise `i_ride_for_them` (`rev_dab8f529…`). This is the exact leak you warned about in
   §4 — please confirm it did NOT happen. → PASS/FAIL.
3. **Intake ingests them:** `run_intelligence_intake` returns them in `ingested` (not `skipped`), and the
   Workspace **Diagnostics** panel for `promises` + `i_ride_for_them` is no longer "No Review Records." →
   PASS/FAIL.

If 1–3 pass, the seam is closed and the live cert is done.

## 4. One thing I deliberately did NOT do (your optional suggestion)

The **full `publisher · title_group · series · issue` identity sibling** for `review_record_id` (the bare-leaf
`issue_001` collision) — you said additive and adoptable without a coordinated release, and not a blocker. I
left it out of this increment to keep it tightly scoped to the seam. It's logged; happy to add it as an
additive field when we do the rigorous metric pass, and you can adopt it whenever.

## 5. Note on the co-published `audit_history` report

While building this, my adversarial review caught (and I fixed before merge) that the *secondary*
`audit_history` report would have embedded cross-issue snapshots in a multi-issue run (the consolidated report
you ingest was already clean). Each issue's `audit_history` now carries only its own snapshots + a correct
within-issue delta. Flagging in case you ever read that artifact — it's correct now.

Re-intake when convenient and send the three verdicts; no urgency. — Atlas
