# Atlas → Johnny + Keystone: SXI-2e done — SXI-2 is now self-refreshing (a single `--all` populates everything)

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform) + Keystone (supervisor). **Date:** 2026-08-12.
**Status:** SXI-2e merged to `main` (`be4add2`); the last SXI-2 piece is in.

> Bridge ground rule honoured: this file is the only thing written here; no Publisher code touched.

---

## 1. The freshness loop is closed

The 2c/2d per-scope + series-comparison views (and Registry-derived Health) read the projections that
`rebuild_discovered` and `rebuild_all` persist. Before 2e they only refreshed on a manual rebuild, so the
tables sat at "—". Now the multi-issue `--all` audit refreshes them automatically after the reports persist
— **recompute-from-below**:

- `--all` (CLI) and `POST /run-delta-audit-all` now, after auditing every issue, rebuild the publisher-wide
  Registry (Health) and the per-scope benchmarks (2c/2d), reporting the outcome under `rebuild` in the
  result.
- It's **best-effort and non-fatal**: the refresh can never turn an audit whose reports are already
  persisted into a failure — a rebuild error is recorded, and a registry failure doesn't block the benchmark
  rebuild.
- Default-off (`rebuild=False`) keeps the certified Increment-1 orchestrator byte-identical; only the two
  `--all` entry points opt in.

Adversarial review confirmed the non-fatal design, correct region resolution, and that it passes the same
ADR-0002 runtime gate the audit already cleared (writes only `edenseek-scout`). Suite 487 green.

## 2. What this means operationally

**One `--all` now does everything:** audits every published issue AND refreshes Health + the per-scope /
series-comparison views. So after the founder runs `SCOUT_RUNTIME_MODE=production …/scout_delta_audit.py
--all` (or clicks Run Delta Audit), the 2c/2d tables populate on their own — no separate rebuild step.

## 3. SXI-2 is complete

`2a` (issue picker) · `2b` (Universe hierarchy + cross-series) · `2c` (per-scope benchmarks + cross-issue
intelligence + comparability guard) · `2d` (series-vs-series) · `2e` (freshness) — all certified-first, all
merged. Composite is deferred per Keystone. Nothing from SXI-2 is outstanding.

## 4. Standing / logged tracks (none blocking)

- **spread_order reading-order axis** — its own track (manual publication → read from published approved
  geometry, not the delta family).
- **Phase-3 rev-to-rev editorial-burden** — the candidate for measuring editorial change across revisions.
- **Perf follow-ups** — uncached whole-bucket scan on scoped intelligence; the double-Discovery on `--all`
  (correctness-neutral) — both worth revisiting when the issue count grows.
- **`audit_ready`/`objects_missing` required-scoping** — latent, no consumer today.

Your ten-minute dashboard walkthroughs drove this entire arc — thank you. Happy to re-drive after deploy and
close the live-cert on 2c/2d once the founder runs `--all`. — Atlas
