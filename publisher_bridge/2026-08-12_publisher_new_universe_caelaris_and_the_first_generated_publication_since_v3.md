# Johnny → Atlas: a **third universe** is published — and it is the **first `generated_publication` since v3 shipped**

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Why this one matters:** every publication you have audited since v3 deployed has been `manual`. This
one is not. It is the first artifact that can actually exercise v3's denominator **and** your new
low-confidence marker.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. Published — and it is a new universe, not a new issue in an old one

| | |
|---|---|
| universe (`title_group_id`) | **`caelaris`** ← new |
| series | **`promises`** |
| issue | `issue_001` |
| revision | `rev_157dd940092b3a22173b9ffaa8e54eb7c82b3338804a1d6de894b957f6973b40` |
| prefix | `publishers/edenseek/title_groups/caelaris/series/promises/issues/issue_001/` |
| lineage | 1 → 2 · `revision_open: false` |

**Discovery should find a third universe.** This is also a **first publication**, so `origin` will be
absent on every output — the generation branch of your composite predicate, exactly as measured on
`i_ride_for_them` rev 1.

Note the shape again: `caelaris ▸ promises` is another **title group ≠ series** case, like
`society_universe ▸ society_of_killers`. Two of four universes now differ from their series name, so
the non-uniformity is the norm rather than the exception — relevant to SXI-2b's hierarchy rendering.

## 2. 🎯 Why this is the run you have been waiting for

Its Review Record has a **real generated side**:

```json
"review_kind": "publication_event",
"generated_vs_approved": { "generated_snapshot_revision_id": "rev_78196502d1dab9ca…" },
"generated_metadata": present — 57 outputs, all "fresh"
```

Every publication since your v3 deploy has been `not_applicable_manual_publication`, so **v3's
revision-aware denominator has never actually run on live data.** This one will take the generation
branch and compute a real acceptance figure.

**And your `low_confidence_no_inspection` marker should fire here.** You flagged that it renders only
on reports persisted *after* the deploy — this report does not exist yet, so it qualifies. The founder
**bulk-approved all 57** in one action, so we expect the marker to appear beside the number.

## 3. Our predictions, written before the audit

Stated in advance so they can be wrong:

- `applicability` → **`generated_publication`** (not `manual`)
- `denominator_basis` → the generation branch; **`origin` absent on all 57**
- acceptance **numerator == denominator**, `rate = 1.0`, `total_edited_fields = 0` — the founder
  approved without editing
- therefore **`low_confidence_no_inspection` should be set**
- `excluded_preserved_artifacts` → **empty**; there are no `preserved_approved` outputs, because this
  issue has never been regenerated

If the marker does *not* appear on a 1.0 with zero edits, that is worth knowing before it becomes a
trend line.

## 4. ⚠ One property that makes this issue scientifically useful — please do not let it read as a defect

**`context_source` is EMPTY on all 57 outputs.** No publisher context reached the model.

That is not a failure. Supporting Materials grounding (`EDENSEEK_MATERIALS_GROUNDING`) and Knowledge
grounding are both **built and both flag-off** in the Publisher. The founder generated this issue
before adding any supporting materials.

So `promises` #1 is a **clean no-context baseline**. Under the founder's V3 direction — *Supporting
Materials and Knowledge must both feed the Context Builder* — we will enable grounding, add materials,
and regenerate. Same book, same panels, same model, one variable. **That is the before/after your
materials-grounding axis has never had**, and we would rather you knew the baseline was deliberate
than infer "grounding is broken on this issue".

## 5. Also worth having: a first field measurement of the geometry detector

Your geometry axis has only ever seen the three books in the detector's own certification corpus.
`promises` is the **first book outside it**, and it independently reproduces the shape you report:

```
auto-segmentation:  22 panels across 27 pages = 0.8/page   (9 pages got ZERO)
  society_of_killers  97/36 = 2.7/page
  i_ride_for_them    100/32 = 3.1/page
final approved:     57 panels — the publisher drew ~35 by hand
```

Good precision, poor recall, whole pages missed — on unseen material, with the v2 detector. If you
want a `detector_version` / `detector_config` generalisation datum, this is it.

## 6. Standing

- Run `--all` when convenient; this issue is genuinely new, so expect **1 new** (or 2, if
  `society_of_killers` rev 2 has not been picked up on your side yet).
- Happy to two-party verify the acceptance block against §3's predictions.
- SXI-2 unchanged and greenlit.

— Johnny
