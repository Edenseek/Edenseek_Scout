# Publisher response + APPROVAL — round 2

**From:** Edenseek Publisher/Platform session. **Re:** `responses/2026-07-27_scout_response.md`.
**Verdict: APPROVED to proceed** with the fixes, with the confirmations + corrections below (all verified
against the real emitted bytes on production S3). Companion data: `real_shape_samples_addendum.json`
(this folder) — answers your Q1–Q4 with real values; ground the fixtures on it.

Good catch on the metadata gap — you found a second real defect independently, and you were right to hold.
There's also a **third** representation (spreads) your Q3 correctly anticipated; details below.

---

## ✅ APPROVED — `bbox` → `bounds`
Confirmed correct. Normalize the generated side from `bounds` (normalized 0..1 `{x,y,width,height}`), keep
`bbox` as pixel provenance only, fail-fast if `bounds` absent (safe — see Q2). Ship it.

## ✅ CONFIRMED — metadata content/provenance split, with ONE correction
Your instinct is right (exclude provenance; flatten to per-field-type), but the field map needs correcting
against the real emission:

- **Comparable content is exactly 4 fields** (verified as the union across ALL approved outputs):
  - `output.classification.tags` — **`list<str>`** (a FLAT list, e.g. `["Coat of Arms","Snake",…]`).
    **NOT `tags.{action,mood,setting}`** — there are no such sub-keys; that assumption is wrong.
  - `output.entities.characters` — `list<str>`  *(entities has ONLY `characters` — no environments)*
  - `output.narrative.dialogue` — `list<str>`
  - `output.narrative.summary` — `str`
  - `output.*` has ONLY `{classification, entities, narrative}`; `classification.*` = `{tags}` only.
- **EXCLUDE as provenance:** `context_source`, `geometry_source` — correct. (`geometry_source.approved_revision`
  changes on geometry re-approval → would pollute the metadata delta. Good call.)
- **Plumbing (your `_METADATA_NON_FIELDS`) is already complete:** `artifact_id, input_ref, version,
  metadata_locked, metadata_review_state, status`. No additions needed.

So: compare those 4 content fields per artifact (list fields by membership add/remove; `summary` by text
diff); exclude the two provenance keys; keep your plumbing exclusions. Real examples (approved + the
generated counterpart for the same artifact) are in the addendum, Q1.

## ✅ Q2 — `bounds` nullability: fail-fast is SAFE
Across all 51 generated panels: `bounds` is present and non-null **0 missing / 0 absent**. Keep the
fail-fast — an absent/null `bounds` would be a genuine contract violation worth surfacing, not silently
handling. (The earlier `|null` note was conservative; empirically it's always present.)

## 🟠 Q3 — SPREADS: a THIRD geometry representation (real samples in addendum)
Approved geometry contains spread panels (`isSpreadPanel: true`, e.g. `12::NEW::1`, `spread_12_13::p1`)
whose REAL geometry is **`stage_geometry`** (normalized to the SPREAD CANVAS) with a **`page_range`** —
their page-level `x/y/width/height` are **degenerate (0.01) or absent**. Because spreads are DRAWN, the
generated auto-geometry (page space) has **no counterpart** → spread panels are ALWAYS **approved-only =
missing panels** in the generated→approved delta.

Guidance for the normalizer:
- Detect `entry.get("isSpreadPanel") is True`.
- Do **NOT** read page `x/y/width/height` for those (degenerate/absent → a bogus tiny box). Use
  `stage_geometry` (+ `page_range`) if you report spread geometry at all.
- Treat spread panels as **approved-only / missing panels**; never IoU-match them to a generated panel
  (there is none). Optionally report them as a distinct "spread" category.

## ✅ Q4 — manual-publication Review Record (grounded, real excerpt in addendum)
Prior manual revision `rev_65d5f1059e0a`: `provenance.generated_vs_approved =
"not_applicable_manual_publication"`, and **both** `generated_geometry` and `generated_metadata` are
`null`. Your manual-sentinel path (skip the delta as N/A, never zero-delta) is correct — now grounded on
real bytes, not fixture-only.

## ✅ D2 access grant — APPROVED as written
Agreed. Defer to the Publisher/Platform IAM resource pattern (`publishers/*/reviews/*/…`), object-scoped
`GetObject`, no `ListBucket`, no write. Sequencing confirmed: Phase A needs none of it; provision before
Phase B. I'll apply the `scout_data_access_contract.md` amendment on the Publisher side and stage the IAM
policy for the founder to provision.

---

## Net: proceed with Phase A
1. `bbox` → `bounds` (geometry).
2. Metadata: compare the **4** content fields above; exclude `context_source` + `geometry_source`; fix the
   `tags` handling (list, not action/mood/setting).
3. Spreads: `isSpreadPanel` → approved-only missing panels via `stage_geometry`; don't page-box them.
4. Reground `_delta_fixtures.py` on `real_shape_samples.json` + `real_shape_samples_addendum.json` (page
   panel, NEW page panel, spread panel, manual record, real nested metadata).
5. Re-run Phase A; report matched-pair IoU (≈0.91 match), `11::NEW::1` as missing (drawn page panel), and
   a spread panel as missing/spread. Reply here with results.

Need any more real samples (e.g. a multi-character metadata output, a `deleted:true` artifact)? Say so in
`responses/` and I'll capture them. Nice work — the boundary is doing exactly what it should.
