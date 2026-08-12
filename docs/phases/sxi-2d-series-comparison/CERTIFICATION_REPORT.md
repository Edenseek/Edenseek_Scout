# Certification Report — SXI-2d (cross-series comparison view)

**Track:** Scout Expansion Increment 2 · sub-increment **2d** (the final SXI-2 increment)
**Branch:** `week12-sxi2d-series-comparison`
**Date:** 2026-08-12 · **Discipline:** certified-first (build → adversarial review → certify → deploy → verify)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for merge → deploy

---

## 1. What changed and why

The last SXI-2 increment: a front-end **series-vs-series** view that consumes SXI-2c's per-scope endpoints,
so a reader can see how series compare — the analytical payoff of the whole multi-issue arc. Composite is
deferred per Keystone (Q2), so this completes SXI-2's approved scope. Pure front-end, read-only.

## 2. Change (`static/index.html`)

- `seriesComparison()` — enumerates series via `/observability/health/series`, maps each to a representative
  `issue_prefix` from `/issues`, and fetches `/benchmark/series?issue_prefix=<rep>` per series in parallel
  and tolerantly (`.catch(()=>null)`). Renders Universe-grouped rows: each series' current-methodology
  precision / recall (geometry) + acceptance (metadata) + health + report count.
- `benchSeg(proj, task)` — the **current-methodology** segment = `segments[points[last].comparability_key]`
  (build_projection sorts entries by run_seq, so the last point is the newest run). Per-task (geometry and
  metadata carry independent comparability keys). `benchRate(bs, metric)` reads `seg.metrics[metric].rate`.
- A series spanning **> 1 methodology segment** gets a `⚠ N methods` flag — the client-side mirror of the
  server comparability guard, so incomparable series are never silently ranked like-for-like.
- Wired into the Intelligence view as a "Compare series" section; renders into its own div (independent
  fetches, never blocks the rest of the view).

## 3. Graceful degradation

`/benchmark/series` 404 (projections not rebuilt yet) → `null` → the row shows "—" and a note that per-series
benchmarks appear once `rebuild_all` has run; the series list + health stay live. `/observability/health/series`
failure shows a scoped message, not a broken view.

## 4. Adversarial review (one round + fold)

The review initially returned **not safe to merge** on one MAJOR — the exact risk flagged for attack. It's
fixed, and everything else was verified safe (tolerance/null paths, metric names, XSS via closed-set
whitelists, `Promise.all` index alignment, and that `points[last]` is genuinely the newest-run methodology).

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| M1 | MAJOR | `repBySeries` keyed the representative issue by **`series_id` alone**, but `series_id` is unique only *within* a universe. Two universes sharing a series name (the Publisher model permits it — `series_health` itself groups on the `(publisher, title_group, series)` triple) would collide onto one `issue_prefix`, silently showing one universe's benchmark on the other's row — believable wrong data in a comparison table. | **Fixed** — `repBySeries` is now keyed and looked up by the full identity (`publisher_id · title_group_id · series_id`), so no cross-universe collision. |
| m1 | MINOR | The `⚠ N methods` flag used `max(geom, meta)` segment counts, conflating two independent comparability axes (a series with 1 geometry + 3 metadata segments implied the precision headline was cross-methodology). | **Improved** — the flag is now per-task (`⚠ geometry/metadata methods`) with a tooltip naming both counts, so it says exactly which headline is current-methodology-only. |
| n1/n2 | NIT | `sample_sizes.reports` interpolated without `esc` (always an int → no XSS); a redundant `try/catch` around `loadIssues`. | Accepted — harmless. |

## 5. Certification statement

Additive, read-only front-end consuming already-certified endpoints; the comparability discipline is carried
into the UI (per-methodology headline + a per-task flag for multi-methodology series); degrades gracefully
before benchmarks are rebuilt. Adversarial review's one MAJOR (cross-universe `series_id` collision) is
fixed and the MINOR improved; the rest verified safe. Suite **482 passed**, JS `node --check` clean.
**Offline-certified.** Remaining gates: merge → deploy (`git pull` + restart) → verify the comparison table
renders (and, once `rebuild_all` has run, shows per-series metrics). With 2d merged, **SXI-2 is complete**
(composite deferred per Keystone).
