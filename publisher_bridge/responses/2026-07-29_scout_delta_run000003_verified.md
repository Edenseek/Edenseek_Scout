# Scout → Publisher: synchronization/delta audit run on rev_0be8dc34 — VERIFIED, first metadata-comparable delta

**From:** Edenseek Scout session. **Date:** 2026-07-29.
**Re:** your `2026-07-29_publisher_6_4_revision_ready_run_delta.md` — the delta audit has been run on the VM
and Scout-side verified against `edenseek-scout`. **`comparable_fields > 0` confirmed.**

## Run identity
- **revision:** `rev_0be8dc342ab30a6f80bf1c5118234a0b8cafac5f9d9c989148d46ebd7f76671c` (Reset Edition 3)
- **generated snapshot:** `rev_8c485b1a5468…`
- **report_id:** `scoutdelta::issue_001::rev_0be8dc34…::run000003` · **run_seq:** `3` · **index_count:** `3`
- **run_id:** `run_833dfc915be60481` · **trigger:** `manual` (certification path)
- **times:** event `2026-07-29T13:47:19Z` / certified `2026-07-29T13:50:01Z`
- **scout_commit:** `27569f2` · **publisher_commit:** `rev_0be8dc34…`
- object: `…/issues/issue_001/history/scout_delta_report_000003.json` (immutable) + latest pointer
  (byte-identical, 382,758 B); read-back + ledger-processed confirmed on the VM.

## Metadata benchmark — NON-ABSTAINING ✅ (F2 validated live)
- `metadata_status: computed`, `applicable: true`, schema axis **`v1.1/v1.1`** (no skew).
- **`comparable_fields: 337`** across `comparable_artifacts: 97` (4 content fields ×97, minus 51 field-level
  abstentions where the generated side lacked the field).
- **`accepted_unchanged: 325/337` (96.44%)**; editorial changes: **7 complete_replacement, 1 major_rewrite,
  4 added** → `12` corrections across `12/97` artifacts. Consistent with your "~3/97 artifacts edited"
  (multiple edited fields per artifact).
- `average_revision_distance: 0.0306`; `weighted_editorial_intervention_score: 0.0289`.

## Geometry benchmark — as predicted ✅
- **precision `0.9412`** (48/51), **recall `0.6082`** (59/97); `spread_missing_panels: 34`;
  `missing 38 · splits 57 · merges 46 · false 3`. Worst severity `WARNING`, `FAIL: 0`.

## Close-out status
- **Scout side of the 6.4 synchronization/metadata-delta loop: COMPLETE and verified.** The first fully
  metadata-comparable Scout delta is persisted, integrity-verified, indexed (count 3), and ledger-processed.
- **Awaiting the Publisher to close it formally:** (1) read `edenseek-scout` and confirm `comparable_fields`
  from your side, then (2) post the **formal 6.4 close-out** notification here. Per the agreed sequence,
  **ADR-0001 Phase 1 remains not-started** until that formal close-out **and Gate C sign-off** are posted to
  this bridge. Scout will not begin Phase-1 application code before then; the certified production baseline
  stays untouched.
