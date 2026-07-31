# Cross-Page Geometry Matching Defect — finding + correction plan

> **Status:** confirmed against production `rev_0be8dc34` (Society of Killers `issue_001`),
> 2026-07-30. Increment 1 (page-scoped matching) fixes it. Discovered while explaining why
> page-stratum precision looked implausibly high (0.973) for 37 generated vs 63 approved panels.

## The defect

`delta_geometry.compute_geometry_delta` matches every generated panel against **every** approved
page panel by IoU on the normalized bbox alone — it never conditions on the panel's **page**.
Panel geometry is normalized **0..1 per page**, so a panel at the top of page 3 has nearly
identical normalized coordinates to the top panel of pages 6, 18, 23. The matcher therefore
pairs panels **across different pages** whenever they share a layout position.

Concrete (production): generated `society_of_killers_1_3::p1` (page **3**) matched approved
panels on pages **3, 6, 18, 23** at IoU 1.00, 0.99, 0.97, 0.84.

## Impact — the certified core metric is inflated

Nearly every generated box finds a positional twin *somewhere* in the book, so almost nothing
counts as a false panel, and one generated panel maps to many approved (and vice-versa),
manufacturing phantom splits/merges.

| Metric | Certified (cross-page) | Page-scoped (correct) |
|---|---:|---:|
| Precision | 0.941 | 0.946 (page stratum) |
| Recall | 0.608 | 0.556 (page stratum) |
| split_rate | 0.588 | **0.0** (phantom) |
| merge_rate | 0.902 | **0.0** (phantom) |

Page-scoped, matching is a clean 1:1 (every generated panel matches exactly one approved panel,
IoU 1.0, or none). The certified `split_rate`/`merge_rate` were almost entirely artifacts.
Combined with the separate spread-stratification fix, the true totals for this revision are
precision ≈ 0.843 / recall ≈ 0.443 — i.e. the certified 0.941/0.608 were **inflated**, not
understated.

## Root cause

- Geometry is normalized per page; the match loop had no `page_number` guard.
- It hid through certification because the delta fixtures placed panels on distinct,
  non-colliding pages (or a single page), so a cross-page collision never occurred in a test.

## Fix (Increment 1 — page-scoped matching)

- **Adapter** (`review_contract_adapter`): guarantee a canonical `page_number` on every page
  panel — prefer the Publisher-carried value, else derive from the artifact-id identity
  (`<property>_<issue>_<page>::pN`, `<page>::NEW::N`), fail-fast if underivable.
- **Delta** (`delta_geometry`): a generated panel may match an approved panel **only when their
  `page_number` is equal**. Bump `GEOMETRY_MATCH_VERSION` `v1 → v2` (a comparability boundary:
  v2 metrics are not directly comparable to v1; the ledger fingerprint changes, so a re-run is a
  clean new `run_id`, never a corruption of archived v1 reports).
- **Tests:** add a cross-page positional-collision case that fails under v1 and passes under v2.

Increment 1 also **excludes spreads (both sides) from the page delta** so the page number is honest
and never regresses. **Increment 2 (done)** adds the actual **spread-to-spread matching in the
spread frame** (scoped by `page_range`): the delta is now **stratified** into page + spread
sub-groups with a micro-averaged whole-issue total. Live `rev_0be8dc34`: page 0.9459/0.5556,
spread 0.5714/0.2353, **total 0.8431/0.4433** (vs the inflated v1 0.941/0.608). **Increment 3** adds
the quality-weighted `E/(A+FP)` accuracy + per-panel resize diagnostics on this corrected foundation.

## Identity is (page, panel)

Every artifact is tied to a `(page_number, panel)` identity. Divergences the accuracy calculation
must account for — **moved/resized** (matched, IoU < 1 → partial credit in Increment 3),
**deleted** (generated, no approved match → false), **added** (approved, no generated match →
missing), **split** (one generated → many approved), **merged** (many generated → one approved) —
are all computed **within a page** so they reflect real editorial corrections, not positional
coincidences across pages.
