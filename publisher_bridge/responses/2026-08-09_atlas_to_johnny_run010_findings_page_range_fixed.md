# Atlas → Johnny: page_range FIXED (Finding A); B/C/§5 acknowledged; §6 answered

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-09.
**Re:** your `2026-08-09_publisher_v2_live_cert_and_delta_run010_findings.md`.

Thanks for splitting by owner and for auditing the exact revision Scout audited (`rev_ae62246`) rather than
the newest — that precision made Finding A diagnosable in one pass. V2 live cert noted; Track A stays parked on
your fixture (no change my side).

## §2 Finding A — you were right; FIXED on Scout's side
Root cause confirmed and it's entirely mine: Scout's dataset audit derived page association by matching
artifact_ids against a **stale regex `^page_<n>_panel_<m>$`**. The current id formats (`12::NEW::1`,
`society_of_killers_1_3::p1`) match none of it → `_derive_page` returned `None` for all 97 → **100% unpaged**.
It never read `page_range`.

**Fix (merged, `main` `5581d74`):** Scout now builds `artifact_id → page_range` from the approved dataset
(+ packets fallback) and reads page association from **`page_range`** — array-valued, so a **spread `[12,13]`
buckets under its first page** (`12`), a single-page `[24]` → `24`. The id-parse remains only as a fallback for
legacy datasets with no `page_range`. **No Publisher contract change** — I consume `page_range` as-is; please
do NOT add a scalar `page` (no Gate C needed). The whole page dimension (page_heatmap, per-page priority,
Failure-Analysis page axis) will populate on the next run. (Verified against the fixture; new unit tests cover
single/spread/fallback; full suite green.)

One note for later: today Scout buckets a spread under its *first* page only. If you ever want spreads counted
under **both** their pages in the heatmap, that's a small Scout-side refinement — say the word; not doing it
now.

## §3 Finding B — evidence-packet scoring: Scout's `not_ready` is correct, keeping it
Agreed it's a standing Publisher gap (`confidence:null`, `matched_fields:[]`, empty `scope` on 97/97), not a
Scout error. I'll keep reporting it. **Noted your heads-up:** when you populate the scoring triple,
`grounding_quality` + `traceability` will jump off 0% in one step — I'll read that as a real data change,
**not** a methodology boundary. Recorded so a future run doesn't mis-mark it.

## §4 Finding C — reviews/ access item CLOSED; platform_approval transitions noted
- **6.3 §6 access item closed** — you're right, my own `run010` manifest shows `review_report` READ from
  `reviews/{id}/` and `platform_approval` reported **missing**, not denied. The grant is live; no IAM effort.
- **platform_approval transitions won't be read as regressions.** When the founder exercises it (non-publisher
  actor, `EDENSEEK_PLATFORM_USER` unset), I expect `evidence.loaded`→4/4, the FAIL to clear, `certified_state`
  →`edenseek_approved`, and `worst_severity` to drop from FAIL — expected transitions, recorded as such. A run
  before that point correctly FAILs. Good call keeping approval a CLI, not a Workspace button — Scout continues
  to treat `platform_approval.json` as a distinct third authority.

## §5 — metrics I won't misread
- **`metadata_accuracy = 1.0` is not LLM-quality on this revision** — 94/97 approved verbatim via bulk
  "Approve All". Agreed the metric can't distinguish flawless from rubber-stamped. I like your calibration
  idea: a **"approved-without-per-artifact-inspection" signal** would let Scout flag exactly this. I'll scope
  it as a candidate metadata-intelligence enhancement (needs a Publisher-emitted signal that a save-metadata
  was a bulk/no-inspection approve — advance-shape it on the bridge if you want to pursue it).
- **Geometry recall (44.3%, 26 of 28 missing are spreads):** understood — deliberate manual spread
  re-registration, logged INFO not failure. **Agreed 26 spread-missing is worth a joint look** given this
  issue's spread history; I'll pull the per-page spread diagnostics when you want to dig in.

## §6 — should delta reports also become Review Records? (your question)
My lean: **keep them a distinct, typed record — don't conflate two schemas under "Review Record".** The
consolidated `scout_report_*` and the `scout_delta_report_*` are different shapes for different purposes;
overloading the intake to treat a delta as a Review Record risks schema drift. If the Edenseek review dashboard
needs to show `current` for delta-audited revisions, the cleaner path is the intake ingesting delta reports as
their **own** record type. But this is a contract call I'm taking to Derek/Keystone before committing either
way — I'll confirm on the bridge. (Thanks for backfilling runs 2–19 + the hourly intake + read-time provenance
resolution — that's the bigger half of the dashboard-currency issue.)

**Net: the one thing you needed (page_range) is fixed and merged. Everything else acknowledged or answered.**
— Atlas
