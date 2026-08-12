# Atlas → Johnny + Keystone: SXI-2c done — the per-scope analytical layer, with the comparability guard proven

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform) + Keystone (supervisor). **Date:** 2026-08-12.
**Status:** merged to `main` (`dcd0919`), adversarially reviewed, pending deploy.

> Bridge ground rule honoured: this file is the only thing written here; no Publisher code touched.

---

## 1. What shipped (server-side; the views land in 2d)

- **Per-scope benchmarks:** `/benchmark/{level}` now serves `publisher` / `series` / `issue`, not just
  `platform`. The persisted per-scope objects `rebuild_all` already writes are now readable at their level.
- **Cross-issue Intelligence:** `/intelligence/geometry` and `/intelligence/metadata` take an optional
  `level` + `issue_prefix`, aggregating recurring failure modes / prompt-model correlations across every
  issue in a scope — the single-issue default is unchanged.

## 2. The comparability guard — inherited and re-proven

The correctness heart of this increment: aggregating metrics across issues must never average across
methodologies. It's **inherited**, not re-implemented — the projection functions segment merged entries by
comparability key, so entries produced under different methodologies land in separate segments regardless of
which issue they came from. A test aggregates two geometry keys across three issues and asserts **2 distinct
segments, not 1**. This is the same "never cross a methodology boundary" discipline the trend lines already
follow, now holding across the whole publisher.

Adversarial review confirmed the guard holds, the scope-prefix filter is boundary-safe (a series
`society_of_killers` scope does **not** swallow a `society_of_killers2` sibling), and a crafted `issue_prefix`
can't be injected into an S3 key. Two MINORs were folded (a boundary test that wasn't actually catching its
regression; a latent context/bucket split). Suite 482 green.

## 3. Nothing needed from the Publisher

2c reads only Scout's own persisted indexes/benchmarks — no contract change, no emission. One perf note for
our own backlog (not yours): a scoped intelligence call currently lists the whole scout keyspace per request;
we'll add caching when the issue count grows.

## 4. Next: SXI-2d — the last SXI-2 sub-increment

Front-end **series-vs-series** and per-scope views that consume these endpoints (composite deferred per
Keystone Q2). After 2d, SXI-2 is complete. I'll build it under the same certified-first cadence.

## 5. Standing

- SXI-2a/2b/2c merged; manual-publication truthfulness live (founder confirmed the F4 findings viewer + the
  platform-approval clear on prod).
- `spread_order` reading-order axis still its own logged track.

— Atlas
