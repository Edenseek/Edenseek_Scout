# D8 · Increment 3 — Cross-Series Health (platform-wide comparison)

> Founder-approved (2026-07-30). Deterministic platform-wide comparison over Series Health — **no new data
> source, no inference, no boundary change.** Recomputable solely from the layer beneath (Series Health) —
> `PRINCIPLES.md` **P2 (Recompute-from-Below)**. Scope: platform-wide only (distribution + attention set +
> summary); **per-publisher comparison deferred** to a later increment.

## 1. User capability
Read-only, platform-wide **Cross-Series Health** — across all publishers/series: the distribution of series
health, the series grouped by status, and the actionable **attention set** (series whose health ≠ healthy,
with issue counts). Surface: `GET /observability/health/cross-series`.
- `summary` — platform-wide series distribution.
- `by_health` — `{healthy: [...], attention: [...], unknown: [...]}` (series prefixes).
- `attention` — the non-healthy series (each with `issue_counts`; drill into Issue Health for reasons).

## 2. Architectural changes
- Additive pure `cross_series_health(registry)` in `scout_observability.py`, **composing `series_health`**;
  reuses the shared summary. Leaf, deterministic, stdlib-only.
- One additive endpoint `/observability/health/cross-series`; all existing routes (incl. certified
  `/observability/health`, `/series`, `/publisher`) unchanged.
- No new data source, no inference (no per-publisher comparison this increment), no Publisher access, no
  writes; advisory only.

## 3. Repository changes
`scout_observability.py` (+`cross_series_health`), `app.py` (+1 route), tests (`test_scout_observability.py`
+4; endpoint test +1), `increment-3-hostile-review.md`, roadmap update in `D8_HEALTH_PROJECTIONS.md`, and
**`PRINCIPLES.md` P2 (Recompute-from-Below)** recorded as a first-class principle. **No new ADR.**

## 4. Certification criteria
`py_compile`; full suite green; **byte-for-byte** existing behavior (`app.py` diff = 1 new route); boundary
unchanged (Registry-only, read-only, advisory); **determinism + recompute-from-below** (a test asserts
`cross_series` summary == `series_health` summary and the attention set == the non-healthy series records);
distribution/grouping/attention coverage + tree-of-one + empty registry; endpoint auth-gated (401 unauth);
hostile review PASS.

## 5. Operator validation (post-deploy, separate)
Authed `/observability/health/cross-series` → `summary {healthy:1,…}`, `attention []`,
`by_health.healthy = [society_of_killers]`; existing endpoints unchanged; no-auth → 401; scheduler/boundary
unaffected.

## 6. Definition of done
Model + endpoint + tests + hostile review + roadmap + P2 recorded; full suite green; hostile review PASS;
byte-for-byte existing behavior; boundary unchanged; **founder-certified → merged**. (Deploy + §5 separate.)
