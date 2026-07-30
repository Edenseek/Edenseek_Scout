# D8 — Health Projections (architecture note + certification record)

> Companion note for the **Registry-Backed Publisher Observability** milestone (ADR-0001 **D8**). Records
> the Health Projection pattern that emerged in Increment 1, the projection roadmap, and the Increment 1
> certification. **No ADR-0001 change** — this realizes D8 within the ratified, frozen architecture.

## The pattern
A **Health Projection** is a **deterministic, read-only view** that derives operational intelligence
**solely from certified Registry data**. Every projection:
- reads only the persisted Registry (Scout-owned `edenseek-scout`) — **no new data source, no Publisher
  read, no write anywhere**; advisory only (Charter §4);
- is **pure** (no wall-clock; carries `registry_generated_at` through so consumers see data freshness);
- emits a **uniform envelope** — `{ projection, health_version, registry_*, summary, records }`.

Shared primitives (in `scout_observability.py`), reused by every projection:
- `assess_issue(entry) -> (health, reasons)` — the atomic per-issue rule (the leaf assessment).
- `roll_up(statuses) -> status` — parent-from-children (any `attention` → `attention`; else all `healthy`
  → `healthy`; else `unknown`). The aggregation rule for Series/Publisher/Cross-Series.
- `_summary(...)` + the envelope.

Health vocabulary: `healthy` / `attention` / `unknown`, with machine reasons (`not_platform_approved`,
`audit_failed`, `audit_pending`, `no_published_revision`).

## Projection roadmap (each a later additive increment; no boundary change)
| Projection | Status | Composition |
|------------|--------|-------------|
| **Issue Health** | ✅ Increment 1 (merged, prod-certified) | `assess_issue` over `registry.entries` |
| **Series Health** | ✅ Increment 2 | `roll_up` over Issue Health grouped by `series_id` (composes `issue_health`) |
| **Publisher Health** | ✅ Increment 2 | `roll_up` over Series Health grouped by `publisher_id` (composes `series_health`) |
| Cross-Series Health | planned | comparison/rollup across series (Registry `tree_view`) |
| Retrieval Health | planned | Registry + retrieval-readiness signals (still read-only, Registry-anchored) |
| Trend Health | planned | health over the report index/benchmark history (time series) |

Routing stays a single `/observability/health` until a second projection justifies a refactor (agreed).

## Increment 1 — certification record (CODE-COMPLETE)
- **Capability:** `GET /observability/health` — per-issue health + platform summary, derived from the Registry.
- **Merged:** `main` `f7952b8` (PR #4). **Rollback point:** `d246563`. Branch `d8-observability`.
- **Certification:** full suite **315 passed**; `py_compile` clean; hostile review **PASS**
  (`increment-1-hostile-review.md`); additive (`app.py` diff = import + one route, no existing route changed);
  boundary preserved (Registry-only, read-only, advisory); leaf module (stdlib only, no cycle);
  drift guards on mirrored constants; deterministic.
- **ADR status:** no change to ADR-0001 (frozen) — Increment 1 realizes D8. This note is the durable
  companion record for the Health Projection layer.
- **NOT deployed** — deployment + operator validation are a separate operational increment
  (`INCREMENT_1_DEPLOYMENT_VALIDATION_PLAN.md`).

## Invariants future projections must preserve
- **Recomputable-from-below (binding).** Every level is a deterministic function of the level beneath it —
  it can always be recomputed solely from that layer (Issue ← Registry; Series ← Issue; Publisher ← Series;
  future Cross-Series/Trend/Recommendations ← the certified layers beneath them). This gives explainability,
  reproducibility, independent testing, and deterministic certification. `roll_up` is a monotone max
  (associative), so composing the levels equals rolling the leaves directly — proven by the coherence test.
- Registry-derived only · deterministic/pure · read-only · advisory (Charter §4) · no new data source · no
  Publisher read/write · Publisher/Scout boundary unchanged · certification-first, one additive increment at
  a time · preserve already-certified endpoints; grow the surface additively.
