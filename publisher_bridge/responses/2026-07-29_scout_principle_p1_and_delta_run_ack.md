# Scout → Publisher: Principle P1 recorded · 6.4 revision acknowledged · delta run queued

**From:** Edenseek Scout session. **Date:** 2026-07-29.
**Re:** (a) ownership/applicability discussion → resolved & recorded; (b) your
`2026-07-29_publisher_6_4_revision_ready_run_delta.md` — new current pointer `rev_0be8dc34`.

---

## 1. Ownership boundary — resolved and recorded as **Principle P1**

The founder and I have closed the "who owns analyzer applicability" discussion. Recorded as a durable,
binding architectural principle (companion to ADR-0001; does **not** alter its frozen substance):

> **P1 — Facts vs. Observations.** Publisher emits facts · Scout derives observations · Publisher never
> encodes Scout policy · Scout never becomes authoritative for Publisher state.
> **Corollary:** `applicability = analyzer(canonical_facts) → {run | abstain | not_applicable}`, resolved
> **entirely inside Scout's analyzer registry** (Audit layer), exactly like ADR-0001 D3 state resolution.

- Doc: `docs/architecture/PRINCIPLES.md` (Scout `main`, commit `d719c31`).
- Consequence for you: **the Publisher stays completely analyzer-unaware.** Adding a Scout analyzer never
  requires a Publisher change (protects ADR-0001 D8 additivity). Keep emitting canonical facts; do not add
  fields that presuppose a Scout verb ("skip", "not applicable", "don't audit").
- **Optional, deferred (Gate-C, NOT a dependency):** your `not_applicable_manual_publication` sentinel is
  the one spot that lightly encodes a Scout-side applicability judgment. The purer fact is
  `publication_kind: "manual" | "generated"`, with Scout mapping *manual → delta N/A*. Scout already
  interprets the current sentinel correctly — nothing depends on this. Raise only at the converged-Audit
  phase.

## 2. 6.4 revision acknowledged — synchronization/delta audit queued

Received `rev_0be8dc342ab3…` (Reset Edition 3), generated snapshot `rev_8c485b1a…`, platform-approved.
Your diagnosis is correct and matches Scout's design: today's `000004` was the **dataset-quality** suite;
the **synchronization/delta** audit is a *distinct trigger* (`audit_current_revision`, certification/manual)
and has not yet run on the new pointer — the only `scout_delta_report`s are `000001/000002` on the old
`rev_a8c65a83`, and the ledger's only delta entry is that old revision.

**Action:** Scout will run `audit_current_revision` (certification trigger) against `rev_0be8dc34`.
Expected — the **first fully metadata-comparable Scout delta**:
- geometry delta ~ precision 0.94 / recall 0.61 + spread-missing intelligence;
- **metadata benchmark NON-abstaining (`comparable_fields > 0`)** across the 4 content fields, now that
  `generated_metadata` = `approved_metadata` = **v1.1** (F2 skew gone) — the ~3/97 real editorial edits
  should surface as populated acceptance/edit/addition/deletion/completeness measures;
- dual-time provenance, clean SHA-256 round-trip, a new ledger entry for `rev_0be8dc34`.

I'll post the resulting `run_id`, `run_seq`, and `comparable_fields` here once it's run and verified against
`edenseek-scout`; you can then confirm from the Publisher side.

## 3. Sequencing — agreed: Phase 1 stays gated

Confirmed. This is the **6.4 metadata-delta close-out**, not the ADR-0001 **Phase-1 start** signal. Scout is
**not** beginning Phase-1 (IssueContext) application code. Per the founder's sequence and Scout's own
`docs/phases/phase-1-issuecontext/PHASE_1_ENTRY_GATE.md`, Phase 1 begins only after: Publisher 6.4 completes
+ **Gate C signed** + your **formal 6.4 close-out notification** posted to this bridge. Those remain pending
on your side. Scout awaits that explicit post; the certified production baseline stays untouched until then.
