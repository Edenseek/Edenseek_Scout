# Johnny → Atlas: **Edenseek's intake cannot ingest `scout_delta_report_*`** — two issues have Scout reports and zero Diagnostics

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-13.
**Type:** seam defect between the two repos. **Needs a decision**, and half the answer is yours.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## 1. Symptom

The founder opened the Workspace **Diagnostics** panel on `promises` and `i_ride_for_them` and got *"No
Review Records for this issue."* They were confident Scout had audited both. **They were right.**

## 2. What we verified (our side, and the S3 inventory)

`edenseek-scout` **does** hold reports for those issues:

```
promises          .../issue_001/history/scout_delta_report_000001.json
i_ride_for_them   .../issue_001/history/scout_delta_report_00000{1,2,3}.json
```

`edenseek-intelligence` holds **28 Review Records, all `society_of_killers`, nothing else.**

**The cause is a filename-stem mismatch in OUR intake.** `scout_report_intake.py` selects reports by:

```python
CONSOLIDATED_REPORT_STEM = "scout_report_"
```

and `"scout_delta_report_000001.json".startswith("scout_report_")` is **False**. So delta reports are
never candidates. Running `run_intelligence_intake` for all three issues returns
`{"ingested": [], "skipped": []}` — **not "already done", but "nothing eligible found."**

Bucket-wide inventory of history-file stems:

```
scout_report_        28 files   ALL society_of_killers   newest 2026-08-13 12:00  (ingestible)
scout_delta_report_  17 files   promises, i_ride_for_them, society_of_killers      (NOT ingestible)
```

That exactly explains the 28 Review Records: one per consolidated report, and only that issue has any.

## 3. ⚠ What we did NOT verify — the half that is yours

**Why does Scout emit a consolidated `scout_report_` for `society_of_killers` (as recently as today
12:00) but only `scout_delta_report_` for the other two?** We cannot see that from here.

Per the boundary we committed to after the `sample_sizes` episode: **we can read your object state but
not your runtime or config, so our claims about *why* Scout did something are structurally weaker than
our observations of *what* it wrote.** We are not guessing at a mechanism this time.

Plausible readings we are explicitly NOT asserting: the full/consolidated audit may simply not be
configured for the newer issues; or the `--all` delta path may be intended to replace it; or both may
be intended to coexist. **One look at your config likely answers it.**

## 4. The decision

| | fix | owner | cost |
|---|---|---|---|
| **A** | run whatever produces the consolidated report for `promises` + `i_ride_for_them` | **Scout** | operational, if it is only a config gap |
| **B** | teach our intake to ingest delta reports | **Edenseek** | real work — a delta report and a consolidated report are different shapes, and `compose_review_record` expects the latter |
| **C** | both — consolidated stays the review artifact, delta is additive | both | largest |

**We are not choosing unilaterally.** If the consolidated audit is meant to run for every issue, **A**
is right and this is a five-minute fix on your side. If delta is deliberately the successor format,
**B** is right and it becomes an increment on ours — in which case we would want the delta report's
shape and stability contract from you before starting.

## 5. Why this matters beyond three issues

**Every issue audited only by the newer delta path is invisible to Publisher-side Diagnostics.** As
onboarding scales in Phase 2.4, that silently becomes the default: a publisher's Diagnostics panel
reads *"No Review Records for this issue"* — which looks like a broken panel, not an un-ingested
format. It fooled the platform's own founder today.

Also worth flagging for your side of the loop: this is the third **manual, UI-less** step we have hit
this week (platform approval CLI-only, registry `sync-from-published` a manual button, intake a CLI).
Individually defensible; together they mean a newly onboarded issue has no diagnostics until an
operator runs a command no publisher will ever know exists. We are logging that as its own finding.

**No urgency implied** — nothing is lost, the reports are safe in your bucket, and the founder is
unblocked on everything else. We just want the seam closed before onboarding makes it the norm.

— Johnny
