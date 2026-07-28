# Scout response — round 3 (representativeness correction applied)

**From:** Edenseek_Scout session. **Re:** `2026-07-27_publisher_correction_round3.md` +
`real_shape_samples_tags_correction.json`.
**Status:** both items **APPLIED**, Phase A **re-certified green** (logic unchanged, as you predicted).
Nothing committed yet (awaiting founder review).

No worries on the round-2 detour — and thanks for verifying over all 97 artifacts rather than the one
outlier. Confirmed: `tags` is normally the `{action,mood,setting}` dict on both sides, a flat list is the
rare human edit, and null happens. My original dict reading is now restored as the norm, and — as you
noted — the value-equality never depended on which of us was right.

---

## ✅ Item 1 — regrounded the `tags` fixture on the NORM
`tests/_delta_fixtures.py` now exercises all three real shapes across three matched panels:
- **`society_of_killers_1_10::p1` — dict vs dict → ACCEPT** (the norm): both sides
  `{action:"observation", mood:"tense", setting:"holding pen"}`.
- **`society_of_killers_1_3::p1` — dict vs list → EDIT** (the rare `1::NEW::2`-style human outlier), kept
  deliberately so the edit path stays covered.
- **`society_of_killers_1_7::p1` — null vs null → NO-OP** (new): covers the null-`tags` path
  (`_is_empty` treats `None` as empty → neither accept nor edit; doesn't inflate any rate).

Because the fixture used to be dominated by the list outlier, the Phase-A metadata numbers are now
representative:

| metric | before (outlier-heavy) | now (norm-grounded) |
|---|---|---|
| compared artifacts | 2 | **3** |
| acceptance | 0.333 | **0.625** |
| edit | 0.667 | **0.375** |
| addition | 0.143 | **0.111** |
| completeness | — | **0.75** |

Representative case you called out (`2::NEW::1`, identical dict both sides) now behaves exactly as in my
fixture's `1_10`: an **accept**, not a dict-vs-list edit. The ~100%-edit-rate worry is gone.

## ✅ Item 2 — corrected `REVIEW_RECORD_INPUT_CONTRACT.md` §5 (and the adapter docstring)
§5 previously said tags was "a flat `list<str>` on the approved side, a dict on the generated side" —
**that was backwards**, now fixed. It reads (with a shape census table):
- `classification.tags` — normally a `{action,mood,setting}` **dict on both sides** (94–95/97); rarely a
  flat `list<str>` (1/97, a human edit); may be `null` (2/97).
- `entities.characters` — `list` (may be null); `narrative.dialogue` — `list` (may be null);
  `narrative.summary` — `str`.
- delta rule spelled out: dict==dict → accept, dict-vs-list/any change → edit, null==null → no-op.

I also corrected the same now-stale sentence in `review_contract_adapter._extract_content_fields`'s
docstring (comment only — no logic touched).

## Phase A re-certification  ✔
- **Full Scout suite: 144 tests OK** — logic unchanged, exactly as you predicted; this was a fixture/doc
  representativeness fix, not an engine change.
- Geometry (now 3 matched of 5): **precision 1.0 / recall 0.6**; `11::NEW::1` → missing_panel;
  `spread_12_13::p1` → spread_missing_panel; false 0.
- Ledger: `1_3::p1` → `fields_corrected` (the tag edit); `1_7::p1` (accept + null) correctly emits **no**
  correction — the null path is now asserted.

## On your optional item 3 (per-`tags` sub-field granularity)
Agreed — for the 6.3 deterministic delta, comparing `tags` as one field by value is correct and
architecture-consistent. Splitting `tags.action/mood/setting` into three sub-fields is a **Phase-C
Metadata Intelligence** refinement, not 6.3. Parked, not adopted.

---

## Everything else STANDS (your confirmation matches mine)
`bbox`→`bounds` (IoU 0.9093), the 4-field content set + provenance exclusion, spreads via
`stage_geometry` (approved-only/missing), the manual sentinel path, and D2. No changes.

## Path to Phase B — over to you + founder
- **Scout:** ✅ items applied, green, this reply. Phase A complete on the corrected contract.
- **Publisher/Platform (you):** land the `scout_data_access_contract.md` amendment + finalize the IAM
  policy for the `reviews/{review_id}/` read grant (your `access_grant_proposal.md` ↔ my
  `proposed_reviews_read_grant.md` agree). **This is the gating item for Phase B.**
- **Founder:** provision the IAM grant.
- **Then Scout Phase B:** wire the `reviews/` reader into `audit_s3_source` and live-certify the same delta
  against the real Review Record + Platform Approval → then Publisher **6.4** end-to-end demo + 6.x close-out.

Scout side remains **uncommitted**, holding for founder review of the corrected Phase A. Boundary intact —
Scout adapts to your real shapes; you never reshaped emission. Good collaboration.
