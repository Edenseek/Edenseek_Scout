# ADR-0001 — Scout Publisher Observability Architecture

**Status:** ACCEPTED (ratified by the Scout session; architecture-frozen).
**Accepted (Publisher/Platform):** 2026-07-28. **Ratified + committed (Scout):** 2026-07-28.
**Originating Publisher bridge document:** `publisher_bridge/ADR-0001-scout-publisher-observability-architecture.md`
(with `publisher_bridge/2026-07-28_publisher_rfc_feedback_observability.md`).
**Deciders:** founder; Publisher/Platform session; Scout session (via `publisher_bridge`).
**Scope:** the Scout (`edenseek-scout`) repository architecture as it generalizes from single-issue
Production Alpha to publisher-wide observability. Does NOT modify the frozen Publisher platform.

---

## Scout Ratification Record

- **Accepted status:** ACCEPTED. This commit is the architecture-freeze point (founder's condition).
- **Acceptance date:** 2026-07-28 (Publisher/Platform accepted; Scout peer-reviewed and ratified same day).
- **Originating Publisher bridge document:** `publisher_bridge/ADR-0001-scout-publisher-observability-architecture.md`;
  Publisher RFC feedback: `publisher_bridge/2026-07-28_publisher_rfc_feedback_observability.md`.
- **Scout peer-review acceptance:** Scout reviewed the ADR + RFC, completed an architecture-verification,
  implementation-readiness, and compliance review, and **accepts** the architecture. There are **no
  required Publisher-side dependencies**; the three Publisher enhancements (approved-revision event;
  wiring `dataset_registry.json` to the 6.2 state machine; a hierarchy/health manifest) are **optional
  future enhancements**. The architecture is implementable **entirely within Scout's own repository
  authority**.
- **Repository ownership boundary (binding):** Publisher (`edenseek-publishing`) owns canonical editorial
  data; Scout (`edenseek-scout`) owns observations/audits/metrics/history/reports; **Scout never writes
  `edenseek-publishing`, never gates/approves a Publisher phase, never becomes the source of truth**
  (IAM-enforced, Phase B 9/9 certified).
- **Binding implementation sequence:** IssueContext → Registry (seeded with the one certified issue) →
  Discovery → scheduler-from-Registry → publisher-wide observability views. Each step additive; the
  certified single-issue production path stays intact throughout.
- **Phase 1 gate condition:** Phase 1 (IssueContext plumbing) application-code implementation begins
  **only after** the Publisher 6.4 demonstration **and** its 6.x close-out are complete (see
  `docs/phases/phase-1-issuecontext/PHASE_1_ENTRY_GATE.md`).

The architectural substance below is the accepted ADR, reproduced without alteration.

---

## Context
Production Alpha (Increment 6.3) certified Scout's Synchronization Audit against a single issue
(`society_of_killers` #1, `rev_a8c65a83a196`): generated-vs-approved geometry + metadata delta, immutable
hash-verified reports, a processed-revision idempotency ledger, and the Repository Ownership boundary
(read-only on `edenseek-publishing`, writes only to `edenseek-scout`, IAM write-denied). Before
generalizing to the whole Publisher repository, the founder and both sessions converged on an architecture
that scales to publisher-wide observability without a future redesign. This ADR records those decisions so
they can be treated as frozen before implementation begins.

## Decisions

### D1 — Repository Ownership Principle (reaffirmed, binding)
The **Publisher** (`edenseek-publishing`) owns canonical editorial data (the authoritative "what exists"
and its state). **Scout** (`edenseek-scout`) owns observations, audits, metrics, history, and reports.
**Scout never mutates Publisher state** — never writes to `edenseek-publishing`, never gates or approves a
Publisher phase, never becomes the source of truth. Enforced by IAM (write-denied) and certified in
Phase B (9/9 access matrix). This boundary is the invariant every other decision preserves.

### D2 — Four-layer architecture: Discovery → Registry → Audit → Publication
- **Discovery** — enumerate the Publisher repository only (Publishers → Title Groups → Series → Issues →
  Approved Contracts / current approved revision). Read-only; no analysis.
- **Registry** — Scout's model of the repository + dispatch state (see D3, D6). The scheduler dispatches
  from the Registry, not by re-scanning S3.
- **Audit** — consume Registry entries; reconstruct the approved contract; run the certified dataset/delta
  audit per issue (the single-issue pipeline generalized to a per-issue context).
- **Publication** — persist derived artifacts (reports, run history, metrics, dashboard data) **only** to
  `edenseek-scout`. No Publisher writes.

### D3 — The Registry is a DERIVED PROJECTION, not a second source of truth
The Registry is a rebuildable projection reconstructable from the Publisher's authoritative objects; it is
Scout's dispatch/observability model, not an authority on "what exists." **Authoritative per-issue state is
resolved from the canonical objects, never from stale Publisher registry fields:** current revision ⇒
`…/issues/{issue}/approved/published.json`; canonical state ⇒ presence of
`reviews/{review_id}/platform_approval.json` (`edenseek_approved`) else `creator_approved`; no pointer ⇒
`draft`. (Note: the Publisher's `registry/dataset_registry.json` approval-status fields are currently stale
and MUST NOT be trusted for state; wiring them to the 6.2 canonical-state machine is a future,
governance-gated Publisher-side change.)

### D4 — The processed-revision ledger remains the idempotency guarantee
The immutable processed-revision ledger stays the dedupe/idempotency contract, keyed to
`(issue, revision, methodology)`: the same publication under the same methodology is never re-audited or
duplicated (event / reconciliation / manual all call one canonical entry). The Registry (dispatch/rollup)
and the ledger (idempotency) are **separate concerns** — the hierarchy/rollup model never absorbs the
idempotency key.

### D5 — IssueContext replaces global environment-based configuration
A per-issue **IssueContext** object (identity + resolved paths + approved-revision + audit context) carries
what a single audit needs, replacing global `SCOUT_APPROVED_S3_PREFIX`-style env configuration. An audit is
a pure function of its IssueContext, which makes single-issue and publisher-wide runs the same code over
different contexts.

### D6 — Registry entries carry the COMPLETE repository hierarchy as first-class structured fields
Every Registry entry stores its full hierarchy path as structured fields — `publisher_id`,
`title_group_id`, `series_id`, `issue_id`, `approved_revision` — plus dispatch/audit fields (last-audited
revision, audit status, timestamps, current metrics). Because the hierarchy is *present in the data on every
entry*, the repository tree (publisher / series / issue rollups, cross-series benchmarking, trends) is a
**query/rollup view over a flat hierarchy-keyed Registry**, not a nested-storage commitment. This is the
structural requirement that makes the Registry a Publisher-repository model without a future migration.

### D7 — Migration strategy: single configured issue → publisher-wide discovery
The current certified single-issue deployment is the **degenerate case** of the same model: a Registry of
one is a tree with one path (one publisher → one title group → one series → one issue). Migration is
generalization, not rewrite: (1) introduce IssueContext (D5) so the audit is context-driven; (2) build the
Registry (D3/D6) seeded with the one certified issue; (3) add Discovery to populate the Registry publisher-
wide; (4) point the scheduler at the Registry (D2). Each step is additive and leaves the certified
production audit path intact; publisher-wide behavior is enabled incrementally, never a big-bang refactor.

### D8 — Why this supports future Publisher Intelligence without structural redesign
Because the Registry models the repository hierarchy (D6) as a derived projection (D3), and the audit is
one producer of observations against it (D2), all future intelligence attaches **additively** as new
observation producers + rollup views over the same model: publisher/series/issue dashboards, cross-series
benchmarking, trend/regression detection, editorial-quality monitoring, and governed intelligence
recommendations. Intelligence stays **advisory** — recommendations enter a governed human-approval workflow;
Scout mutates no detector/prompt/model/schema/Publisher data (SCOUT_CHARTER). This realizes the platform's
recorded Publisher-Knowledge / cross-system-observatory direction without changing the substrate.

## Consequences
- **Positive:** publisher-wide scaling with no redesign; one code path for single-issue and publisher-wide
  (IssueContext); the ownership boundary and idempotency contract are preserved and explicit; intelligence
  is additive.
- **Costs/risks (managed):** the hierarchy model must not be over-built ahead of data — implement the
  tree-of-one now, add rollup views as issues accumulate; the Registry must stay a rebuildable projection
  (never a second source of truth); Discovery must derive state from authoritative objects, not the stale
  `dataset_registry.json`.
- **Access:** publisher-wide read is already covered by the provisioned v5 grant
  (`EdenseekScoutPublishingReadAccess`: `GetObject` on `publishers/*/…/{approved,processing,reviews}/*` +
  `registry/*`, `ListBucket`, writes denied) — **no IAM change needed**.

## Sequencing (binding)
Implementation of this architecture begins **after** the Week-11 exit criterion — the 6.4 end-to-end
demonstration + the 6.x close-out — is complete. The ADR may be frozen now; the Discovery refactor is a
Phase-C-boundary activity (it overlaps the Scout Synchronization Audit milestone / C1 Publisher Intelligence
Foundation). Any change this architecture requires in the **Publisher** repository (e.g. wiring
`dataset_registry.json` to the 6.2 state machine, a Publisher-emitted approved-revision event, a hierarchy/
health manifest) is Publisher/Platform-owned and **governance-gated (Gate C)** — never built inside a Scout
phase.

---

## Ratification actions (completed by the Scout session)
1. **Ratified + adopted:** this canonical Scout copy committed at
   `docs/architecture/ADR-0001-scout-publisher-observability-architecture.md` — the architecture-freeze point.
2. **Implementation sequence recorded** (D7); Phase 1 execution-control package prepared under
   `docs/phases/phase-1-issuecontext/` (brief, runbook, hostile-review, entry gate). **No application code
   written.**
3. **No Publisher-side dependency to start** — confirmed; all reads are covered by the certified contract +
   the v5 grant. Any genuine Publisher need surfaced during implementation goes through the bridge +
   Publisher governance (Gate C).
4. **Bridge reply posted** confirming ratification: `publisher_bridge/responses/2026-07-28_scout_adr_ratification.md`.
