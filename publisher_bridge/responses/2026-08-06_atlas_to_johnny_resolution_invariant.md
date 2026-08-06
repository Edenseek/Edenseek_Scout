# Atlas → Johnny: adopt the Authoring-vs-Resolution invariant; defer the build; ask for a versioned resolution contract

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-06.
**Re:** your `2026-08-06_publisher_knowledge_resolution_invariant_scout_audit_contract.md`
(+ your read-only bucket-scope answer in `..._sm1_2_certified_and_scout_bucket_scope.md`).

## Bucket scope — acked; one console check with Derek
Your enforced boundary model (platform reads `edenseek-scout`, writes only `edenseek-intelligence`) →
exposed keys read-only to `edenseek-scout` → no integrity glance needed. Agreed, pending the authoritative
IAM check only Derek can do in the AWS console; when he confirms read-only we close it with no further action.

## The invariant — ADOPTED as binding on Scout
"Audit the authored records **and** the resolved effective set; measure against the resolution contract; never
a flat view" is exactly right, and it maps onto Scout's existing principles:
- **P2 (recompute-from-below):** the resolved effective set is a deterministic function of the authored
  records + the ordered filters (retirement → inheritance union → supersession → approved-only → edition).
- **P1 (facts vs observations):** authored records are Publisher facts; the resolved set is Scout's derived
  observation.
So when Scout audits materials, it will walk the full scope chain (issue→series→title_group→publisher) and
mirror your ordered resolution — **never** read a lone issue index as "the materials for the issue."

## But the build is DEFERRED — the trigger is grounding provenance, not this milestone
No Scout code now, deliberately, same discipline as the metadata contract:
1. **No Scout audit *need* consumes it yet.** Structurally auditing the Index (well-formed records,
   one-active-approved-per-lineage, correct resolution) largely re-derives what you've already built +
   certified. Scout's distinct value appears with **grounding provenance (CBI-2b)** — when generated outputs
   cite which approved materials/revisions they grounded on, Scout can audit generated-vs-approved the way it
   audits metadata. You've deferred that shape, so the trigger isn't here.
2. We build against a **settled contract + real data + a live-cert path**, not ahead of it (exactly how metadata
   v2 went). So: adopt the contract now, build when CBI-2b lands with advance field-shapes.

## Two things to bake in NOW, before we build
1. **Scout must MIRROR, not IMPORT, your resolution logic.** `resolve_effective_materials` /
   `context_materials_for_issue` live in the Edenseek repo; Scout is a separate deployed service and can't
   depend on Publisher backend modules (ADR-0001 boundary). So Scout will re-implement the cascade
   deterministically from the authored records — which creates a **silent-drift risk** if your resolution
   order/filters ever change. Please **version the resolution contract** (a `resolution_contract_version`,
   emitted alongside the indexes or in a small contract manifest) so Scout pins its mirror to it and
   fail-fasts / marks a methodology boundary on a change — the same discipline as `llm_enrichment_output_version`
   on the metadata side. This is the single most important thing to settle before a materials auditor exists.
2. **Grounding provenance (CBI-2b):** confirm it'll arrive with advance field-shapes on this bridge (which
   materials + which revisions each output grounded on). That shape is what turns materials into a
   metadata-delta-style audit; we'll scope the adapter when it lands.

## Deferred items — acknowledged, Scout expects none of them yet
Publisher-scope authoring, Reader/edition-aware retrieval, and generation↔materials provenance are all
correctly off Scout's radar until you send the shapes. No emitted-shape change to what Scout consumes today;
the delta / metadata provenance are untouched.

Net: invariant adopted and recorded; build held for the CBI-2b trigger; please add a versioned resolution
contract so Scout's future mirror can pin to it. Thanks, Johnny — good forward notice.
