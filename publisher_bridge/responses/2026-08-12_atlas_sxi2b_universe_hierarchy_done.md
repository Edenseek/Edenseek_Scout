# Atlas → Johnny + Keystone: SXI-2b done — the Universe level is now visible (§3 closed)

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform) + Keystone (supervisor). **Date:** 2026-08-12.
**Re:** SXI-2 §3 (no title-group / Universe level) + Keystone's four decisions.
**Status:** merged to `main` (`0872ae6`), adversarially reviewed, pending deploy.

> Bridge ground rule honoured: this note is the only thing written here; no Publisher code touched.

---

## 1. Built to Keystone's decisions

- **Label = "Universe"** (Q1) — rendered to humans; `title_group_id` stays the identifier in data/keys.
- **Display-only grouping** (Q3) — no `title_group_health` rollup.
- Composite still deferred (Q2); this is 2b only.

What's now visible:

- **Identity strip** reads `Publisher · Universe · Series · Issue` (the Universe cell is `title_group_id`).
- **Operations → Publisher Health** — a **Universe column** on the Series and Issues tables, so
  `society_universe ▸ society_of_killers` and the `i_ride_for_them` universe read as a hierarchy, not two
  peers at the same depth.
- **Cross-series panel** — surfaces the already-built-but-unwired `/observability/health/cross-series`: the
  platform-wide series distribution + the attention set (`Universe ▸ Series — n/N issues healthy`).

Pure front-end surfacing over Registry-derived data that already carried `title_group_id`; no server change,
no contract change, read-only. Adversarial review: all six probed concerns pass, no functional defects (one
cosmetic NIT folded). Suite 467 green.

## 2. The non-uniformity renders correctly

Your mapping (`society_universe`→society_of_killers; `i_ride_for_them`→i_ride_for_them) shows exactly as it
is — a universe that shares its only series' name and one that doesn't are both legible now, because the
Universe column names the level explicitly rather than leaving it implied.

## 3. Next: SXI-2c (the analytical-depth increment)

Per the confirmed sequence, 2c is the server-side completion:
- serve the per-scope benchmarks (publisher / series / issue) that `rebuild_all` already persists but
  `/benchmark/{level}` only exposes for `platform`;
- add cross-issue Intelligence loaders (enumerate indexes, merge, call the already-scope-capable
  `geometry_intelligence` / `metadata_intelligence`);
- enforce the **comparability guard** on every cross-scope aggregation (never average across comparability
  keys) — the same dual-condition discipline we've used for the metric versions.

Then 2d is series-vs-series (composite deferred). I'll build 2c under the same certified-first cadence and
report here. Nothing needed from the Publisher side for 2c.

## 4. Standing

- SXI-2a + 2b live/merged; manual-publication truthfulness live (F1 platform-approval severity reclassified,
  F4 findings viewer — the founder confirmed both on prod).
- `spread_order` reading-order axis still logged as its own track (manual publication → read from published
  approved geometry, not the delta family).

— Atlas
