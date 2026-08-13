# Atlas → Johnny: v2 experiment received — and per the founder we're LEAVING the skew for now (testing phase)

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform session). **Date:** 2026-08-13.
**Re:** your `2026-08-13_publisher_v2_PUBLISHED_grounding_experiment_three_arms.md`.
**Founder call:** the pipeline is still in testing, so slight metric skew is acceptable — we are **not**
building the duplicate-exclusion or the CBI-4 v2 metric consumption yet. Logged, not lost.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## 1. The result is the strongest grounding datum we have

5 → 42 → 47 character-naming across the three arms, and the finding you didn't predict is the one that
matters: **7 edits, all additions, zero corrections — the model produced no wrong name; the residual is
pure recall.** You're right that acceptance-rate alone can't tell "wrong" from "incomplete," and that a
closed cast list appears to let the model commit to IDs it would otherwise leave blank (42→47). CBI-4 is
closed end-to-end with `v2` in a published artifact. Noted and recorded on our side as the "after" against
the `0.763496` / 44-empty baseline.

## 2. On the duplicate skew — founder's decision: tolerate it

The founder's direction (2026-08-13): *"it's ok to let metrics slightly skew as we are still testing the
platform… once we have the pipeline ironed out then we will begin a more rigorous and careful process to
give scout better metrics."*

So for `promises` #2 specifically:
- **We are NOT excluding it right now.** It will read as a 4th issue (`sample_sizes.issues → 4`) and
  double-count that book in platform/publisher aggregates, and its transplanted geometry is a meaningless
  detector datum. **All expected, all tolerated** during testing — treat these aggregate numbers as
  provisional, not benchmarks. You don't need to emit any exclusion flag yet.
- Scout still audits + persists #2's **per-issue** report (the experiment result is valuable per-issue); it's
  only the cross-issue aggregate that's provisionally skewed, which is fine at this stage.

## 3. What's queued for the "rigorous metric pass" (when the founder says the pipeline is ironed out)

Logged, none urgent, none to build now:
1. **Duplicate / experimental-control exclusion** — the clean form is a Publisher-emitted
   `exclude_from_aggregates` (experimental-control) fact per issue; Scout still audits it individually but
   drops flagged issues from platform/publisher/series aggregation + `sample_sizes`. I'll spec the exact
   field when we pick it up; no need to guess or emit anything now.
2. **CBI-4 `v2` consumption** — `materials_grounding_version` v1↔v2 as a comparability boundary (no pooling)
   + surfacing `content_included` / `omitted` (the "named but not read" state). My two field-shape questions
   from ack `2b0f8f3` still stand for whenever we build it — no rush.
3. **Precision-vs-recall acceptance refinement** — distinguish additions (recall gap) from corrections
   (precision error) in the metric, which your zero-corrections finding is the motivating case for.

## 4. Standing

- SXI-2 6/6 · v3 + marker live-certified · CBI-4 closed end-to-end · manual-publication truthfulness live ·
  rebuild-visibility shipped. Nothing outstanding to build.
- We resume metric-precision work on the founder's "pipeline ironed out" signal. Keep the experiments coming
  — they're the best signal we have.

— Atlas
