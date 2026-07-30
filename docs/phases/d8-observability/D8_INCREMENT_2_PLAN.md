# D8 · Increment 2 — Series & Publisher Health (deterministic rollups)

> Founder-approved (2026-07-30). Pure deterministic aggregation over the Registry — **no new data source, no
> inference, no boundary change.** Each level is a projection computed **solely from the level beneath it**:
> `issue_health` → `series_health` → `publisher_health`.

## 1. User capability
Two read-only advisory rollup views:
- **Series Health** (`GET /observability/health/series`) — per series, `roll_up` over its issues' healths +
  child issue counts.
- **Publisher Health** (`GET /observability/health/publisher`) — per publisher, `roll_up` over its series'
  healths + series/issue counts.
The certified **`/observability/health` (Issue Health) is preserved exactly** — the two rollups are additive
sub-routes.

## 2. Architectural changes
- Additive pure functions in `scout_observability.py`: `series_health(registry)` (composes `issue_health`) and
  `publisher_health(registry)` (composes `series_health`), reusing `assess_issue` / `roll_up` / `_summary` +
  a shared `_envelope`. Leaf, deterministic, stdlib-only.
- API refactor point (now justified): extend the `/observability/health` namespace **additively** with
  `/series` + `/publisher`; the certified route is unchanged (no parameterization of it).
- **Coherence:** `roll_up` is a monotone max over `attention > unknown > healthy`, hence associative — the
  composed hierarchy equals rolling leaves directly (asserted by test).

## 3. Repository changes
`scout_observability.py` (+2 functions + `_envelope`/`_series_prefix`), `app.py` (+2 routes), tests
(`test_scout_observability.py` +8; endpoint tests +2), `increment-2-hostile-review.md`, roadmap update in
`D8_HEALTH_PROJECTIONS.md`. **No new ADR.**

## 4. Certification criteria
`py_compile`; full suite green; **byte-for-byte** existing behavior (`app.py` diff = 2 new routes; certified
`/observability/health` + `issue_health` unchanged); boundary unchanged (Registry-only, read-only, advisory);
determinism + the associativity/coherence property; auth-gated endpoints (401 unauth); hostile review PASS.

## 5. Operator validation (post-deploy, separate)
Authed `/observability/health/series` → `society_of_killers = healthy`; `/observability/health/publisher` →
`edenseek = healthy`; existing `/observability/health` + `/registry` unchanged; no-auth → 401; scheduler
unaffected; no Publisher writes.

## 6. Definition of done
Model + 2 endpoints + tests + hostile review + roadmap update; full suite green; hostile review PASS;
byte-for-byte existing behavior; boundary unchanged; **founder-certified → merged**. (Deploy + §5 separate.)
