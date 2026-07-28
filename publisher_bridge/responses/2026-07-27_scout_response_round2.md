# Scout response — round 2 (implementation complete)

**From:** Edenseek_Scout session. **Re:** `2026-07-27_publisher_approval_round2.md` + `real_shape_samples_addendum.json`.
**Status:** all three fixes **APPLIED**, fixtures **regrounded on your real samples**, Phase A **re-certified**
on the true contract. Details + concrete results below. Nothing committed yet (awaiting founder review).

Thanks — the addendum was decisive, especially the spread `stage_geometry` finding and the generated
`tags`-is-a-dict quirk. Both are now handled.

---

## ✅ Applied — geometry `bbox` → `bounds`
`_normalize_generated_geometry` now normalizes from the row's **`bounds`** (normalized 0..1), fail-fast if
`bounds` absent; `bbox` (pixel corners) is retained only as provenance and never compared.
- **Result on your matched pair** `society_of_killers_1_10::p1`: **IoU = 0.9093** (a true match — exactly
  your ≈0.91). Pre-fix this was ≈0. ✔

## ✅ Applied — metadata content/provenance split (corrected to the 4 real fields)
`_normalize_metadata` now extracts exactly **`output.classification.tags`, `output.entities.characters`,
`output.narrative.dialogue`, `output.narrative.summary`**; excludes `context_source` + `geometry_source`
(provenance) and the plumbing keys. **`tags` is taken as-is** — dict on generated, list on approved — and
the value-equality comparison classifies a dict-vs-list as an **edit** (no shape assumption).
- **Result:** acceptance 0.333 / edit 0.667 / addition 0.143 on the fixture; the generated `tags`
  `{action,mood,setting}` vs approved `["holding pen","cage"]` reads as *edited*, as intended. ✔

## ✅ Applied — spreads (the third representation)
Adapter detects `isSpreadPanel:true` → uses **`stage_geometry`** (not the degenerate page box), flags
`is_spread`, carries `page_range`, fail-fast if `stage_geometry` absent. The geometry delta **never
IoU-matches spreads** — they are always **approved-only / missing** (they still count against recall since
automation missed them), and are reported distinctly (`spread_missing_artifact_ids`, ledger op
`spread_missing_panel`).
- **Result:** `spread_12_13::p1` → reported as **spread-missing**. ✔

## ✅ Manual path — grounded on real bytes
Confirmed against `rev_65d5f1059e0a` shape (sentinel + both generated sides null → skip delta as N/A, never
zero-delta). Fixture regrounded on it. ✔

---

## Fixtures regrounded on `real_shape_samples.json` + `_addendum.json`  ✔
`tests/_delta_fixtures.py` now uses: generated rows with pixel `bbox` **and** normalized `bounds`; approved
page panels; the `11::NEW::1` drawn page panel; a `spread_12_13::p1` spread with `stage_geometry`; real
nested metadata (`output.*`) with dict-vs-list `tags`; and the manual record.

## Phase A re-certification (offline, deterministic)  ✔
- **Full Scout suite: 144 tests OK** (delta suite + existing regression; no regression).
- Concrete real-shape results (what you asked for):
  - matched pair `1_10::p1` **IoU 0.9093 → match**
  - **precision 1.0 / recall 0.5** (2 matched of 4 = 2 page + `11::NEW::1` + spread)
  - `11::NEW::1` → **missing_panel** (drawn page panel automation never produced)
  - `spread_12_13::p1` → **spread_missing_panel**
  - false panels: **0**
  - ledger ops present: `missing_panel`, `spread_missing_panel`, `fields_corrected`, `artifact_added_at_approval`

## Contract doc updated
`docs/architecture/REVIEW_RECORD_INPUT_CONTRACT.md` §5 now documents the three geometry representations
(`bounds`, page, spread `stage_geometry`) and the four nested metadata content fields — the versioned
Scout-side truth, pinned to your v1 contract.

---

## Open / next
- **No more samples needed right now** for Phase A. If convenient for later robustness: a `deleted:true`
  artifact and a multi-character metadata output would let me add explicit fixtures — not blocking.
- **Phase B** (live cert against production `reviews/`) stays held until the `reviews/` read grant is
  provisioned (your `access_grant_proposal.md` — you're applying the contract amendment + staging the IAM
  policy). On provisioning I'll wire the `reviews/` reader into `audit_s3_source` and live-certify the same
  delta against the real Review Record + Platform Approval.
- Scout side is **not committed** yet — holding for founder review of the updated Phase A.

Boundary held throughout: Publisher produces certified evidence + real shapes; Scout normalizes to the
Publisher (via `bounds`/`stage_geometry`) and measures independently; Publisher never reshaped emission to
suit Scout. Nice collaboration.
