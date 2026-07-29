# Scout Architectural Principles

> Durable, cross-phase principles that constrain implementation. **Companion to
> `ADR-0001-scout-publisher-observability-architecture.md`** — these clarify how the ADR's decisions
> are applied; they do **not** alter the frozen ADR substance. Preserve them during every
> implementation phase. New principles are appended; existing ones are not silently changed
> (a change is a deliberate, recorded decision).

---

## P1 — Facts vs. Observations (the ownership boundary, sharpened)

**Statement.**
- **Publisher emits facts.** The Publisher (`edenseek-publishing`) publishes canonical, self-descriptive
  facts about what happened: `revision`, `schema_version`, `publication_kind` (generated / manual),
  approved artifacts, provenance, and available evidence. These are facts the Publisher would emit whether
  or not Scout existed.
- **Scout derives observations.** Scout (`edenseek-scout`) interprets those facts into observations —
  audits, metrics, history, reports, and **analyzer applicability**.
- **Publisher never encodes Scout policy.** The Publisher must not emit values that presuppose a Scout
  concept ("skip metadata", "not applicable to comparison", "don't audit"). Observation policy is Scout's.
- **Scout never becomes authoritative for Publisher state.** Scout resolves state and applicability *from*
  canonical objects; it never overrides or replaces the Publisher as the source of truth.

**Corollary — applicability is a pure function of canonical facts.**
Analyzer applicability is resolved **entirely within Scout's analyzer registry** (the Audit layer) as a
deterministic function of Publisher-emitted facts — exactly like state resolution (ADR-0001 D3). Each
analyzer decides for itself, from the facts, whether it runs / abstains / is N/A:
```
applicability = analyzer(canonical_facts) -> { run | abstain | not_applicable }
```
Examples (all fact-driven, all Scout-owned): metadata analyzer *abstains* when generated vs approved
enrichment schema versions differ; the generated-vs-approved delta is *N/A* for a manual publication
(no generated side); dataset-quality *always applies*.

**Why this is binding (ties to ADR-0001).**
- **D8 (additivity):** analyzers must attach without any Publisher change. If applicability lived on the
  Publisher side, adding a new Scout analyzer would force a Publisher change — forbidden. The Publisher
  stays completely **analyzer-unaware**.
- **D3 (derive from canonical objects):** applicability is derived from facts, never from stale/opinionated
  Publisher fields.
- **D1 (ownership):** interpretation is the observation side of the boundary; keeping applicability in
  Scout *protects* the boundary in both directions (the Publisher can't gate Scout's observation; Scout
  can't author Publisher state).

**Optional, deferred refinement (semantic, NOT a dependency).**
The Publisher's `not_applicable_manual_publication` sentinel slightly encodes a consumer-applicability
judgment rather than a pure fact. The purer fact is `publication_kind: "manual" | "generated"`, with Scout
mapping *manual → delta analyzer N/A*. This is an **optional future Publisher naming/semantics refinement
(Gate-C)** — Scout already interprets the current sentinel correctly, so nothing depends on it. Raise it on
the bridge only when the converged-Audit phase makes it worthwhile; do not build ahead of governance.

**Where it applies.** Governs the Audit layer / analyzer-registry design (the converged, revision-oriented
audit). It does not affect Phase 1 (IssueContext) directly, but must hold once analyzers are orchestrated.

**Provenance.** Derived from ADR-0001 (D1/D2/D3/D8); converged in the Publisher↔Scout bridge discussion,
recorded 2026-07-29. Ownership discussion considered **resolved**; revisit only if implementation surfaces a
real contradiction.
