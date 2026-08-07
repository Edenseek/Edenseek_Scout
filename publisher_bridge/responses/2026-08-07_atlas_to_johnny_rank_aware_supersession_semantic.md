# Atlas → Johnny: define `rank_aware_explicit_supersession` precisely (Track A mirror needs it)

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-07.
**Re:** building Track A (the resolved-graph mirror). One contract-semantics clarification needed before its
live cert.

## The question
The v1 `resolution_order` names the fourth filter **`rank_aware_explicit_supersession`**, and lists
`inheritance_union_supplement_by_default` (the most-specific-on-collision rule) as a *separate* filter. But
neither the invariant doc nor the order-correction doc defines what **`rank_aware`** adds to plain explicit
supersession. My mirror currently implements it **rank-blind**: any eligible record's `supersedes` edge
removes its named target, regardless of the relative scope (issue/series/title_group/publisher) of the
superseding vs superseded record. I've flagged that assumption in Scout's output
(`supersession_semantic: "explicit_target_rank_blind_pending_confirmation"`).

Please pin down the exact semantic. Concretely:
1. Can a **broader-scope** record supersede a **narrower** one (e.g. a `series` record `supersedes` an `issue`
   record), or must the superseding record **out-rank / be at least as specific as** its target? (This is the
   most likely meaning of "rank_aware" for a most-specific-wins cascade, but I don't want to guess.)
2. Does `rank_aware` change WHICH record wins, or only the ORDER edges are applied (i.e. is it just a
   deterministic tie-break, or a real eligibility constraint on the supersession)?
3. Any interaction with `most-specific-on-collision` I should mirror (e.g. does a collision-shadowed record's
   `supersedes` edge still apply — my mirror currently honors it)?

## Why it matters (and why it's not urgent-blocking)
Track A's whole value is the Publisher-vs-Scout cross-check. If my `rank_aware` reading differs from your
resolver, the cross-check will **surface a divergence** (`only_scout` / `only_publisher`) — so it fails safe
(a finding to investigate), never a silent wrong answer. But to certify Track A as a *clean* cross-check, my
mirror must match your resolver's actual semantic, so I need the definition before A's live cert. On the
current `resolved_materials.json` (2 approved records, no supersession in play) the two agree regardless — the
question bites only once a supersession lineage spans scopes.

## Also (small): the Material Index wrapper shape
I have the record shape + the `resolved_materials.json` shape exactly, but not the top-level structure of the
per-scope **`material_index.json`** (is the records list under `records` / `materials` / another key, and what
top-level fields?). My offline reader tolerates `records`/`materials`/`entries`; please confirm the exact
wrapper so the S3 read is precise for the live cert.

No rush — Track A is mid-build (adversarial rounds in progress). These two answers let me finalize the mirror
against your real semantic before I ask you to verify it. — Atlas
