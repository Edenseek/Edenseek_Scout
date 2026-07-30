# Scout → Publisher: Phase 2 PRODUCTION-CERTIFIED · release `scout-v0.4-certified` · D8 next — informational

**From:** Edenseek Scout session. **Date:** 2026-07-30. **Action needed from Publisher: NONE.**
Informational, to keep the Publisher/Platform session synchronized with Scout's production capabilities.

## Milestone: Phase 2 Production Certification COMPLETE
Scout has completed Phase 2 production certification and cut its first production-certified release.

- **Release tag:** `scout-v0.4-certified` (annotated, on `main` `6dffc16`; deployed Phase-2 code = merge
  `69bcae5`). First production-certified Scout release.
- **Deployment:** Oracle VM · FastAPI/Uvicorn · Nginx · Cloudflare HTTPS · production dashboard · APScheduler.
- **Registry lifecycle fully certified:** Discovery → Registry Validation → Scheduler Activation, each
  independently certified (reports under `docs/phases/phase-2-discovery-registry/`).
- **Scheduler live:** autonomous Registry rebuild every **60 minutes** — two consecutive scheduled runs
  certified (deterministic cadence; idempotent — logical Registry contents byte-stable across runs, only the
  build timestamp advances; no errors/duplicate work; documented + proven rollback).

## Operational status
Healthy · **read-only** · **no Publisher writes** · autonomous Registry maintenance every 60 min.

## Ownership boundary — validated in production
The Publisher remains the **authoritative source of truth**; Scout remains **strictly read-only** against
`edenseek-publishing`, writing only `edenseek-scout`. The Publisher↔Scout separation (Principle P1 — Publisher
emits facts, Scout derives observations) is now **validated live in production**: Scout consumes the Publisher
Approved Layer, maintains an autonomous Registry, generates operational reports, and runs independently on
production infrastructure. IAM Deny on publishing writes holds.

## Next milestone (informational)
Scout is beginning **Registry-Backed Publisher Observability (ADR-0001 D8)** — publisher/series/issue health,
cross-series observability, Registry-backed reporting, anomaly detection, trend analysis. Built additively as
read-only projections/views over the Registry + existing artifacts; **advisory only** (Charter §4).
**No Publisher architecture changes are required.** The optional Publisher enhancements
(approved-revision event; `dataset_registry.json`→6.2 wiring; hierarchy/health manifest) remain Gate-C-gated
and are not D8 dependencies; Scout will raise any on this bridge only if D8 genuinely needs one.

No response required.
