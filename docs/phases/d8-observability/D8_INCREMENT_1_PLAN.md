# D8 · Increment 1 — Registry-Backed **Issue Health** (as the first Health Projection)

> ADR-0001 **D8** (Publisher Observability), realized additively. Founder-approved (2026-07-30) with the
> architectural framing: introduce a general **Health Projection** capability, of which **Issue Health** is
> the first concrete projection. Single `/observability/health` route for now — routing is refactored only
> when a second projection exists.

## 1. User capability
A read-only **Issue Health view**: per-issue advisory health (`healthy` / `attention` / `unknown` + machine
reasons) derived solely from the Registry, plus a platform summary. Surface: `GET /observability/health`.
- `healthy` = `state == edenseek_approved` **and** `audit_state == audited` (approved + currently audited).
- `attention` = published but not platform-approved and/or audit failed/pending (reasons:
  `not_platform_approved`, `audit_failed`, `audit_pending`).
- `unknown` = no published revision (`no_published_revision`).

## 2. Architectural changes
- **New leaf module `scout_observability.py`** — a general Health Projection capability. Increment 1 ships:
  - `assess_issue(entry)` — the atomic per-issue rule (every projection's leaf assessment);
  - `roll_up(statuses)` — the parent-from-children primitive Series/Publisher/Cross-Series health will reuse;
  - `_summary` + a uniform projection envelope (`projection` name + `summary` + `records`);
  - `issue_health(registry)` — the first concrete projection.
  Pure, stdlib-only, no I/O, no Scout-module imports (leaf).
- **One additive endpoint** in `app.py` (`GET /observability/health`): `load_registry()` → `issue_health(...)`,
  try/except → 503 (same contract as `/registry`). No existing route changed.
- **Nothing else** — no change to Registry/Discovery/scheduler/audit path/Registry schema/Publisher boundary.

**Long-term fit:** Series / Publisher / Cross-Series / Trend / Retrieval health are later additive
increments composing `assess_issue` + `roll_up` + `_summary` over the Registry's `rollup`/`tree_view`.

## 3. ADRs / repo updates
- **No new ADR** — realizes ADR-0001 D8 within the ratified architecture + Principle P1.
- New: `scout_observability.py`, `tests/test_scout_observability.py`; `app.py` +1 route; `+`endpoint tests;
  `docs/phases/d8-observability/` (this plan + the hostile review). No Publisher/bridge change.

## 4. Certification criteria
- `py_compile` clean; **full test suite green**.
- **Byte-for-byte** existing behavior — `app.py` diff = import + one route; no existing route touched.
- **Boundary unchanged** — reads only the persisted Registry (`edenseek-scout`); **no Publisher read, no
  write anywhere**; advisory only.
- **Correctness/determinism** — all health states + reasons, the rollup rule, summary counts; drift guards
  on mirrored constants; pure (no wall-clock).
- **Endpoint** — auth-gated (401 unauth), 503 on error (never 500), correct projection body.
- **Hostile review: PASS.**

## 5. Operator validation (post-deploy, separate)
After a future (separate) deploy: authed `GET /observability/health` → `summary {healthy:1, attention:0,
unknown:0, total:1}` and `issue_001 = healthy`; unauth → 401. This increment makes no production change itself.

## 6. Definition of done
Module + endpoint + tests + hostile review on the `d8-observability` branch; full suite green; hostile review
PASS; byte-for-byte existing behavior; boundary unchanged; **founder-certified → merged**. (Deploy + §5 are
separate lifecycle steps.)
