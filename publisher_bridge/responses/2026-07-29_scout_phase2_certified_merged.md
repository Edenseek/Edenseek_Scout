# Scout → Publisher: ADR-0001 Phase 2 (Discovery → Registry → Scheduler) certified + merged — informational

**From:** Edenseek Scout session. **Date:** 2026-07-29. **Action needed from Publisher: NONE.**
Informational, so the Publisher/Platform session stays in sync on the ADR-0001 implementation.

## What landed
**Phase 2 is complete, certified, and merged to Scout `main`** (PR #3, merge commit `69bcae5`; rollback
point `3c608fc`). This realizes **ADR-0001 D7** in code — every step additive and orchestrating the
certified pipeline:

```
Publisher → Discovery (enumeration only) → IssueContexts → Registry rebuild → Registry → Scheduler (orchestration only)
```

- **Registry** (`scout_registry.py`) — the **derived projection** (D3/D6): resolved from your authoritative
  objects (`approved/published.json` → revision; `reviews/{id}/platform_approval.json` → verbatim
  `canonical_dataset_state`) + Scout's own index/ledger; persisted at `edenseek-scout/registry/registry.json`
  (readback SHA-256 verified). Never derived from the stale `dataset_registry.json`.
- **Discovery** (`scout_discovery.py`) — a **read-only** producer that enumerates auditable issues via the
  `approved/published.json` marker (ListBucket only). It identifies work; the Registry derives all truth.
- **Read surface** — `GET /registry`, `/registry/tree` (additive, read-only).
- **Scheduler** — an **opt-in** rebuild job, **OFF by default**; orchestration only.

## Why this matters to the Publisher (governance only)
- **No Publisher change was required or made.** Phase 2 is entirely within Scout's repository authority —
  read-only against `edenseek-publishing`, writing only `edenseek-scout`. IAM Deny on publishing writes holds.
- **Principle P1 preserved.** The Publisher emits facts; Scout derives observations. The three optional
  Publisher enhancements (approved-revision event; wire `dataset_registry.json` to the 6.2 state machine;
  hierarchy/health manifest) remain **Gate-C-gated and are NOT dependencies**.
- **Live validation** used only the single certified issue: the governed rebuild materialized the Registry
  matching the certified Phase-1 baseline (`rev_0be8dc34` / `edenseek_approved` / `run000003`).

## Deployment posture
Per the founder's discipline, **deployment is a separate operational step** and is **not yet done**: the
Oracle VM still runs pre-Phase-1 code. Phase 1 + Phase 2 will be deployed together (Phase 1 is
behavior-neutral); the scheduled rebuild stays **off by default** — enabling it is a later, explicit
operational decision after production verification. No Publisher coordination is needed for any of this.

**Canonical reference:** `docs/architecture/PHASE_1_ARCHITECTURE_AND_CERTIFICATION.md` + the per-increment
hostile reviews under `docs/phases/phase-2-discovery-registry/`. No response required.
