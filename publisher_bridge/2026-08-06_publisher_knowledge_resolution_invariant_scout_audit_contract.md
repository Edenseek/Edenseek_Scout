# Johnny → Atlas: Knowledge Resolution Invariant — Scout must audit RESOLVED, not flat

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-06.
**Re:** the SM write/approval path is now live + certified (the audit surface I pre-announced), and a
new BINDING platform invariant that governs how Scout audits it.

---

## 1. Milestone — the Supporting Materials authoring vertical is COMPLETE + certified + pushed
Since SM-1.2/1.3, the whole vertical landed on `week12-day2-knowledge-migration` (origin `9231fb5`),
each increment certify-before-advance (Gate B + several live-S3 certs):
- **Write/approval lifecycle** (WPG-2b-1..4): approve · retire/discard · revise (supersede) · bind
  edition — append-only, one active `publisher_approved` per lineage (proven by construction).
- **Scope authoring** (SCOPE-1/2/2b/3): records authored at **issue / series / title_group (Universe)**
  scope; Publisher scope deferred. Live-S3 certified for series + title_group.
- **Revise carry-forward + remove** (WPG-2b-3b/3c): assets carried by reference / removed, append-only.
- **Edition binding** (WPG-2b-4) + **edition-aware resolution primitive** (CBI-3a).

So the per-scope **Material Index is now a real audit surface** — it holds authored records with a full
lifecycle. Certified Publisher/PAL/geometry/publication/Reader behavior remains byte-identical.

## 2. BINDING platform invariant (founder-ratified 2026-08-06) — Authoring vs Resolution
Spec in the Edenseek repo: `docs/architecture/knowledge_authoring_vs_resolution_invariant.md`
(+ the SM realization `supporting_materials_scope_inheritance_invariant.md`). Summary:
- **Authoring (write once):** a record is authored **exactly once at a chosen scope**
  (Publisher → Universe/Title Group → Series → Issue → Edition refinement); **never duplicated** at
  descendants; scope is explicit, not inferred.
- **Resolution (derive at read time):** the effective set for an operation is **computed** by walking
  **broadest → narrowest** and applying, in order: **retirement exclusion → inheritance union
  (supplement-by-default, most-specific kept) → rank-aware explicit supersession → lifecycle/approval
  (publisher_approved-only) → edition filter**. Nothing is copied down; the effective view is derived.

**This governs Scout too.** Per the invariant, Scout "audits authored records and the resolved
effective sets — measures against the resolution contract, does **not** re-implement a flat view."

## 3. Concrete ask — how Scout should audit the Material Index
1. **Do NOT read a single issue index in isolation and treat it as "the materials for the issue."** A
   record eligible for an issue may be authored at series/title_group/publisher scope and inherited.
   Auditing a lone issue index will UNDER-count (miss inherited) and mis-judge supersession.
2. **Audit two distinct things, matching the invariant:**
   - **Authoring layer:** each per-scope Material Index's records (identity, scope.level, lifecycle
     status, append-only history, one-active-approved-per-lineage).
   - **Resolved layer:** the effective set for a target (issue [+ optional published edition]) = the
     cascade walk (issue→series→title_group→publisher) with the ordered filters above.
3. **Canonical resolution entry points** (Edenseek repo, `backend/app/repository/`): `load_scope_chain`
   → `material_index_merge.resolve_effective_materials(indexes, target_edition_id=None)` →
   `context_builder_view` (approved-only); composed as `material_index_resolve.context_materials_for_issue
   (scope, target_edition_id)`. Mirror this contract; do not hand-roll a flat scan.

## 4. S3 placement shapes (so Scout knows where to look, read-only)
Per-scope Material Index JSON at `reference/material_index/material_index.json` under each scope root:
- issue: `publishers/{p}/title_groups/{t}/series/{s}/issues/{i}/reference/material_index/…`
- series: `publishers/{p}/title_groups/{t}/series/{s}/reference/material_index/…`
- title_group: `publishers/{p}/title_groups/{t}/reference/material_index/…`
- (publisher: `publishers/{p}/reference/material_index/…` — read path exists; authoring deferred)

Record shape: `{material_id, category, subtype, scope:{level, …, edition_id?}, title, status
(draft|publisher_approved|retired|superseded), version, files:[{file_id, role, artifact_ref:{stage,
sub, revision}, region?}], relationships:[{rel:"supersedes", target:{kind:"material", id}}…]}`. File
bytes are first-class content-addressed PAL artifacts under `reference/materials/{material_id}/{file_id}/`.
Edition-bound records carry `scope.edition_id` (a published Edition revision id).

## 5. Deferred — what Scout should NOT expect yet
- **Grounding provenance (CBI-2b)** — which approved materials/revisions each generated output grounded
  on is **not emitted yet**. Don't audit generation↔materials provenance until I send that shape.
- **Publisher-scope authoring** — no records at publisher scope yet (resolution already loads that level).
- **Reader cover surfaces / edition-aware retrieval** — the edition filter's read consumer is a future
  Reader increment; today edition binding is a verified tag only.

No emitted-shape change to anything Scout already consumes (the delta / metadata provenance are
untouched). This is additive: a new, richer audit surface + the resolution contract to audit it by.
Advance shapes for CBI-2b provenance will come on this bridge before it lands, as before.

— Johnny
