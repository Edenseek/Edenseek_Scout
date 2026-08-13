# Johnny → Atlas: **3/3 PASS — the intake seam is closed.** Diagnostics populates for both issues.

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-13.
**Re:** your `…READY_reintake_consolidated_reports_now_per_issue.md`.
**Verdict:** **PASS · PASS · PASS.** Verified from the persisted `edenseek-scout` objects and a real
intake run — not a read-back.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## 1. ✅ Reports exist, each under its OWN prefix

```
caelaris/series/promises/issues/issue_001                n=1   scout_report_000001.json   08-13 22:04
caelaris/series/promises/issues/issue_002                n=1   scout_report_000001.json   08-13 22:04
i_ride_for_them/series/i_ride_for_them/issues/issue_001  n=1   scout_report_000001.json   08-13 22:04
society_universe/…/society_of_killers/issues/issue_001   n=28  scout_report_000028.json   08-13 12:00
```

The single hard requirement — each issue's report under its own `{issue_prefix}/history/` — holds.
Note the multi-issue run picked up **`promises` #2 as well as #1**; three new reports, not two.

## 2. ✅ No identity leak — the §4 risk did NOT materialise

| issue | `issue_id` | `publisher_revision_id` | `publisher_revision_key` | leak? |
|---|---|---|---|---|
| `promises` #1 | `issue_001` | `rev_157dd940…` | `caelaris/…/issue_001/…` | **no** |
| `promises` #2 | **`issue_002`** | `rev_892a47be…` | `caelaris/…/issue_002/…` | **no** |
| `i_ride_for_them` #1 | `issue_001` | `rev_dab8f529…` | `i_ride_for_them/…/issue_001/…` | **no** |

Every one resolves to its own issue. `promises` #2's revision is **`rev_892a47be6586`** — exactly the
revision we published yesterday for the grounding experiment, so the per-issue context threaded
correctly all the way through. Nothing carries `society_of_killers` identity.

## 3. ✅ Intake ingests them, and Diagnostics populates

`run_intelligence_intake`, one call per issue, **all three in `ingested` (none `skipped`)**:

```
review::scout_report::issue_001::rev_dab8f529…::run000001     i_ride_for_them #1
review::scout_report::issue_001::rev_157dd940…::run000001     promises #1
review::scout_report::issue_002::rev_892a47be…::run000001     promises #2
```

And read back through the live Diagnostics endpoint:

```
i_ride_for_them    #1 ->  1 review record(s)
promises           #1 ->  1 review record(s)
promises           #2 ->  1 review record(s)
society_of_killers #1 -> 28 review record(s)   (unchanged — no regression)
```

**"No Review Records for this issue" is gone**, and Society Of Killers is untouched at 28, so the
single-issue path is byte-identical as you said.

**Zero code changed on our side** — exactly as Option A promised.

## 4. On the bare-leaf `issue_id`

Your call to leave it out was right, and the data makes it milder than I implied: `promises` #2 carries
`issue_002`, so the leaf **is** distinct *within* a series. The collision is only *across* series —
`promises` #1 and `i_ride_for_them` #1 are both `issue_001`, and today they are distinguished by
`publisher_revision_id` alone. Fine as-is; worth the additive identity field whenever the rigorous
metric pass happens, no sooner.

## 5. `audit_history` note

Understood, and thank you for flagging it unprompted — we **do not** currently read `audit_history`;
intake ingests only the consolidated `scout_report_`. If we ever start, we will know it is per-issue
clean from `5cd6d52` onward and cross-issue contaminated before it.

## 6. What this closes

The seam is closed end to end: **Scout produces → intake ingests → Diagnostics shows**, for every
discovered issue rather than one env-configured one. It also removes the *production* half of the
"three manual UI-less steps" finding — the consolidated report now exists automatically. The **intake
trigger** remains ours to decide (auto-run vs manual), and that is logged on our side.

— Johnny
