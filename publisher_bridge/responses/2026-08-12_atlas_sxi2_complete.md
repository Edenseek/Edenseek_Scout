# Atlas → Johnny + Keystone: SXI-2 is complete — the multi-issue dashboard is done (composite deferred)

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform) + Keystone (supervisor). **Date:** 2026-08-12.
**Status:** SXI-2d merged to `main` (`5e823b9`); all approved SXI-2 scope shipped.

> Bridge ground rule honoured: this file is the only thing written here; no Publisher code touched.

---

## 1. SXI-2 shipped, end to end

Starting from Johnny's dashboard walkthrough (§2 reachability, §3 no Universe level), the full arc is done:

- **2a — issue picker** (§2): the analytical views are selectable per discovered issue. *(live-verified.)*
- **2b — Universe hierarchy** (§3): `Publisher · Universe · Series · Issue` in the identity strip + a Universe
  column on the Operations tables + the cross-series health panel. Label "Universe", identifier
  `title_group_id`, display-only.
- **2c — per-scope analytical layer**: `/benchmark/{level}` serves publisher/series/issue; cross-issue
  Intelligence loaders + scoped `/intelligence/*`; the comparability guard proven across issues.
- **2d — cross-series comparison**: a "Compare series" table on Intelligence — each series' current-methodology
  benchmark headline (precision/recall/acceptance), Universe-grouped, with a per-task methodology-boundary
  flag so incomparable series are never ranked like-for-like.

**Composite/overall is deferred per Keystone (Q2)** — so this is the complete approved scope. Every increment
went through the certified-first cadence (build → adversarial review → fold → certify → merge); the reviews
caught and I fixed real defects along the way, including 2d's cross-universe `series_id` collision — exactly
the "a universe may share its series' name" case Johnny flagged.

## 2. One dependency to make the numbers appear: rebuild the benchmarks

The 2d comparison table and the 2c per-scope benchmarks read the persisted projections `rebuild_all` writes.
Until those are rebuilt, the series rows show "—" (the series list + health are live regardless). Wiring the
Registry/benchmark rebuild to run automatically after the multi-issue `--all` audit is **SXI-2e**, the one
remaining freshness item from the original scope — small, and I'll pick it up next unless Keystone wants it
sequenced differently. For now the founder can populate them by running the benchmark rebuild once.

## 3. Nothing needed from the Publisher

All of SXI-2 was surfacing + server-side completion over Scout's own Registry/index/benchmark data — no
contract change, no emission, read-only throughout.

## 4. Standing / open tracks

- **SXI-2e** (rebuild freshness) — the last piece to make 2c/2d numbers auto-populate.
- **spread_order reading-order axis** — still its own track (manual publication → read from published approved
  geometry, not the delta family; base64 location noted).
- **Phase-3 rev-to-rev editorial-burden** — the logged candidate for measuring editorial change across
  revisions (the blind spot Johnny raised).
- **Accepted follow-ups** from 2c reviews: uncached whole-bucket scan on scoped intelligence (perf, when the
  issue count grows); `audit_ready`/`objects_missing` required-scoping (latent).

Thanks for the ten-minute walkthroughs — they were the best defect-finding tool in this whole increment. — Atlas
