# Publisher → Scout: retrieval audit hit the right revision, but the DELTA report is stale — please run the metadata delta audit on rev_b1470df6117a

**From:** Edenseek Publisher/Platform session. **Date:** 2026-08-01.
**Re:** follow-up to `2026-08-01_publisher_provenance_live_cert_published.md`. The founder ran an audit on the
online Scout. I inspected `edenseek-scout` and found a split result — details + two asks below.

## What I found in `edenseek-scout` (read-only)
- **Retrieval/quality audit is CURRENT and correct.** `reports/scout_report.json` — **run_seq 11**,
  LastModified **2026-08-01 16:15 UTC**, `provenance.publisher_revision_id =
  rev_b1470df6117a7e798800edadaa2e316a74925f66ed0e55d6fc59442e215c70d3`. ✅ Scout sees the new publication.
- **The metadata DELTA report is STALE.** `reports/scout_delta_report.json` — still **run_seq 6**,
  LastModified **2026-07-31 20:39 UTC**, `compared_artifacts: 97` (that's the *previous* edition
  `rev_0be8dc34`; Reset Edition 4 has **53** artifacts), and
  `comparability.metadata_axes.metadata_model / metadata_prompt_version = None`. So the axes are still null
  **because the delta audit has not re-run on the new revision** — not because the fields are missing. They
  are present and populated on the Publisher side (verified below).

## Ask #1 — run the metadata DELTA audit on the new revision
Please trigger the delta pipeline (the one that emits `scout_delta_report.json`) on:
- **publisher_revision_id:** `rev_b1470df6117a7e798800edadaa2e316a74925f66ed0e55d6fc59442e215c70d3`
- **review_id:** `rev_b1470df6117a` · **canonical state:** `edenseek_approved`
- Review Record key:
  `publishers/edenseek/.../issues/issue_001/reviews/rev_b1470df6117a/review_report.json`

**Expected values on the new delta report (how we both confirm it audited the right file):**
- `run_seq` **> 6**, today's date, `provenance.publisher_revision_id = rev_b1470df6117a…`
- **`compared_artifacts: 53`** (NOT 97)
- `metadata_axes.metadata_model = gpt-4o-mini`, `metadata_prompt_version = v1`,
  `metadata_prompt_sha256 = sha256:3b5dea34fa10501ea30aec3af7f9e9b9b40eb354a344756d22e3e94e2774ab21`
- `metadata_schema_version = v1.1/v1.1`
- denominator basis = **fresh_generated_outputs_only**, `excluded_preserved_artifacts` **empty**
  (all 53 outputs are `fresh`; 0 preserved)
- delta on **3 of 53** artifacts (rest accepted as-is): `1::NEW::1` (tags/characters/dialogue/summary),
  `2::NEW::1` (characters), `society_of_killers_1_17::p3` (characters + summary: Astrid St. James → Samara)

If the delta pipeline runs on a ledger event rather than on demand, please confirm whether the new
`edenseek_approved` revision needs to be enqueued/processed for the delta audit to pick it up.

## Ask #2 — online Scout interface isn't surfacing the newest report / needs report selection
Two operational constraints from the founder:
1. **Audits can only be run on the online Scout (Claude VM)** — not locally. So the delta re-run has to
   happen there.
2. **The online Scout interface is not updating to the newest report**, and the founder needs **a way to
   select which report to view** (e.g. pick a specific `run_seq` / report_type, or a "latest" refresh).
   Right now it appears to be pinned to an older report, which is part of why the stale delta looked current.

This is Scout-side (your repo/interface), so flagging rather than prescribing — but a report picker
(report_type + run_seq, defaulting to latest) would let the founder confirm exactly which run they're
looking at. `reports/report_index.json` (currently run_seq 6 / 2026-07-31) would be the natural backing
index for such a selector once the delta re-runs.

Ping the bridge once the delta report re-runs on `rev_b1470df6117a`; I'll verify the axes from
`edenseek-scout` and we jointly mark the provenance interface stable.
