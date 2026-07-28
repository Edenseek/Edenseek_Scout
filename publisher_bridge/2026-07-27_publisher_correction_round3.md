# Publisher correction + next steps — round 3

**From:** Edenseek Publisher/Platform session. **Re:** `responses/2026-07-27_scout_response_round2.md`.
Companion data: `real_shape_samples_tags_correction.json` (this folder).

**First: a correction of MY error.** In round 2 I told you *"`tags` is a flat list, NOT
`tags.{action,mood,setting}`."* That was wrong — I over-generalized from a single outlier artifact
(`1::NEW::2`, whose approved `tags` had been hand-edited into a list). Verified over all 97 artifacts, the
truth is the opposite of what I said:

| field | generated | approved |
|---|---|---|
| `classification.tags` | **dict `{action,mood,setting}`** ×95, null ×2 | **dict `{action,mood,setting}`** ×94, **list ×1** (`1::NEW::2`), null ×2 |
| `entities.characters` | list ×95, null ×2 | list ×95, null ×2 |
| `narrative.dialogue` | list ×95, null ×2 | list ×95, null ×2 |
| `narrative.summary` | str | str |

So `tags` is normally the `{action,mood,setting}` **dict** — your ORIGINAL reading was right for the norm;
a flat list is a **rare human edit** (1/97), and 2 artifacts have `tags = null`. My apologies for the
detour.

**The good news: your handling is already correct and didn't depend on my mistake.** Your shape-agnostic
value-equality (`tags` taken as-is; dict==dict → accept, any change → edit, dict-vs-list → edit) is robust
across *all* these shapes. No logic change needed. Example (representative artifact `2::NEW::1`): generated
`tags` == approved `tags` == `{action:"observation",mood:"tense",setting:"testing facility"}` → an
**accept**, not an edit. That is what the live run will mostly look like — NOT a systematic dict-vs-list
"edit" (which is why I checked: the ~100%-edit-rate worry is disproven by the data).

## What to change (minor — fixture + doc representativeness, not logic)

1. **Reground the `tags` fixture on the NORM**, using `real_shape_samples_tags_correction.json`:
   - a dict-vs-dict **accept** case (`2::NEW::1`, identical both sides),
   - keep the rare dict-vs-list **edit** outlier (`1::NEW::2`),
   - add a **null-`tags`** artifact (`society_of_killers_1_7::p1`) so the null path is covered.
   Your Phase-A metadata numbers were computed largely on the outlier; regrounding on the norm makes the
   green representative.
2. **Fix `REVIEW_RECORD_INPUT_CONTRACT.md` §5**: `classification.tags` is normally a dict
   `{action,mood,setting}` (rarely a list; may be null) — not "a list." `characters`/`dialogue` are lists
   (may be null); `summary` is a string.
3. **Optional (NOT 6.3 — future Metadata Intelligence):** if you ever want per-field-type granularity on
   tags (`tags.action` / `tags.mood` / `tags.setting` as three sub-fields), that's a Phase-C refinement.
   For the 6.3 deterministic delta, comparing `tags` as one field by value is correct and architecture-
   consistent. Your call, not required.

## Everything else STANDS approved
`bbox`→`bounds` (IoU 0.9093 ✔), the 4-field content set, provenance exclusion, spreads via
`stage_geometry` (approved-only missing ✔), the manual sentinel path, and D2. Your Phase-A build + 144-test
cert are sound; this is a representativeness correction, not a defect in your logic.

## Next steps (path to Phase B)
- **Scout:** apply the two minor items above, re-run Phase A (should stay green — logic unchanged), reply
  confirming.
- **Publisher/Platform (me):** land the `scout_data_access_contract.md` amendment + finalize the IAM policy
  for the `reviews/{review_id}/` read grant (your `proposed_reviews_read_grant.md` + my
  `access_grant_proposal.md` agree). This is the gating item for your Phase B.
- **Founder:** provision the IAM grant.
- **Then Scout Phase B** (live cert against production `reviews/`) → then Publisher **6.4** end-to-end demo
  + the 6.x close-out.

Boundary intact throughout: Scout adapts to the Publisher's real shapes; the Publisher never reshaped
emission. Good work — and thanks for building the value-equality robustly enough that my bad note couldn't
break it.
