# Scout → Publisher: ADR-0001 Phase 1 (IssueContext) certified + merged — informational

**From:** Edenseek Scout session. **Date:** 2026-07-29. **Action needed from Publisher: NONE.**
Informational, so the Publisher/Platform session stays in sync on the ADR-0001 implementation.

## What landed
**Phase 1 (IssueContext plumbing) is complete, certified, and merged to Scout `main`** (PR #2, merge commit
`fe07303`; rollback point `b24d058`). It introduces `IssueContext` — the canonical per-issue execution
context — and threads it as an **optional** parameter through Scout's read path, evidence layer, runners,
persistence, index, ledger, and projections.

- **Behavior-neutral.** With `context=None` (what every path uses today) Scout runs byte-for-byte as before.
  `IssueContext.from_env()` is **not activated** in any execution path.
- **Not deployed.** The Oracle VM still runs the pre-Phase-1 code; deploying Phase 1 is a separate later
  decision. The certified single-issue behavior is unchanged.
- **Certified.** Full suite 260 passed; single-issue **production re-cert** reproduced `run000003` exactly
  (`run_id run_833dfc915be60481`, fingerprint `fp_580cbeb1f41b`) and reconciled idempotently; hostile-review
  checklist PASS.

## Why this matters to the Publisher (governance only)
- **No Publisher change was required or made.** Phase 1 is entirely within Scout's repository authority
  (`edenseek-scout`), read-only against `edenseek-publishing` + the certified contract.
- **Principle P1 preserved.** The Publisher stays analyzer-unaware; Scout derives observations + analyzer
  applicability. The three optional Publisher enhancements (approved-revision event; wire
  `dataset_registry.json` to the 6.2 state machine; hierarchy/health manifest) remain **Gate-C-gated and are
  NOT Phase-2 dependencies**.

## What's next
Scout will begin **Phase 2 (Discovery → Registry)** from this certified baseline on the founder's go-ahead.
Per ADR-0001 D3, the Registry will be a **derived projection** resolved from canonical objects
(`approved/published.json`, `reviews/{id}/platform_approval.json`) — **never** the stale Publisher
`dataset_registry.json`. If Phase 2 surfaces a genuine need for one of the optional Publisher enhancements,
Scout will raise it here as a Gate-C proposal first.

**Canonical reference:** `docs/architecture/PHASE_1_ARCHITECTURE_AND_CERTIFICATION.md` (Scout repo).
No response required.
