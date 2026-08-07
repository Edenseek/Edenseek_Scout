# Certification Report — Track A: Resolved-Graph Material Auditor

**Track:** Week 12 · Supporting Materials · **Branch:** `week12-track-a-resolved-graph-auditor`
**Date:** 2026-08-07 · **Discipline:** certified-first (build → 2 adversarial rounds → certify → deploy → live cert)
**Status:** CODE-COMPLETE · adversarially reviewed (3 rounds) · **offline-certified against the Publisher-
CONFIRMED semantic** · LIVE cert needs only a Phase-B read path (both contract questions now answered).

## 0. Update — both live-cert gates ANSWERED (2026-08-07), mirror corrected + re-verified
Johnny confirmed both open items from the authoritative resolver (`material_index_merge.py`):
- **`rank_aware_explicit_supersession`:** R suppresses T iff **`rank(T) > rank(R)`** (T strictly LESS specific);
  broader can't suppress narrower; same-scope is a no-op (lifecycle `superseded` status handles it); only
  surviving non-suppressed records suppress (most-specific-first); collision-shadowed records' edges are
  DROPPED. Scout's mirror was corrected to this — **this reversed round-1 fix #3** (that reviewer was wrong
  about shadowed edges; only the authoritative source settled it). A 3rd adversarial round cross-read the real
  resolver and found **no divergence on valid data**; order-independence **proven** (5000 permutations → one
  result). Added a `binding_status == "bound"` gate mirroring the resolver's `supersedes_ids()`, and a
  `materials.cross_scope_collision` authoring finding.
- **`material_index.json` wrapper:** `{schema_version:int, scope, records:[...]}` — records under `records`
  (the tolerant reader already handles it).
- **Documented low-severity out-of-band boundary:** an unknown `scope.level` maps to rank 99 (the Publisher
  derives rank from index position 0–3); only reachable on malformed placement the store forbids.
`supersession_semantic` now reports `rank_aware_strict_more_specific`. Suite 429.

## 1. What it is
Scout's **independent mirror** of the Publisher's certified Supporting-Materials resolution cascade, which
**cross-checks** Scout's computed effective approved-material set against the Publisher's own emitted
`resolved_materials.json`. Two independent implementations agreeing is the certification; a divergence is a
finding on one side (Principle P1/P2). Read-and-advise; mirror-not-import (ADR-0001 — Scout can't depend on
Publisher backend modules, so it re-implements the cascade and pins to the contract version).

## 2. What it computes (`materials_resolution_audit.py`)
- **The mirror** (`resolve_effective_materials`) follows the corrected v1 contract semantic:
  `retirement_exclusion` + `edition_filter` as per-record ELIGIBILITY gates applied DURING the inheritance
  union (before supersession) → most-specific-on-collision (issue<series<title_group<publisher) →
  `rank_aware_explicit_supersession` → `lifecycle_publisher_approved_only` (TERMINAL, the Publisher's
  `context_builder_view`).
- **The cross-check** (`compute_resolution_audit`): Scout's effective set vs `resolved_materials.resolved` →
  `matches` / `agree` / `only_scout` / `only_publisher` / `file_revision_mismatches` / `duplicate_resolved_ids`.
  Pinned to `resolution_contract_version` (fail-fast on unknown); a manifest-vs-snapshot version skew abstains.
- **Authoring invariants** (`_authoring_findings`): dangling `supersedes`; >1 active `publisher_approved` per
  lineage (union-find over supersedes edges); superseded-still-approved.
- Identifiers/references only (material_id / file_id / revision) — never material bytes/text. Deterministic.

## 3. Adversarial review (two rounds, independent)
**Round 1** found 5; all addressed. **Round 2** verified them and found one NEW crash the round-1 fix
introduced; fixed + regression-tested.

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | minor | `sorted()` over file tuples crashed on a `None` file_id/revision. | Total-order `_sorted_files` key; str-coercion only in the sort key (stored values stay real, so no false match — verified). |
| 2 | **major (uncertain)** | `rank_aware_explicit_supersession` is implemented rank-blind, but **no contract doc defines `rank_aware`**. | Kept the faithful explicit-target reading; **flagged** in code + report (`supersession_semantic: "explicit_target_rank_blind_pending_confirmation"`); **raised to the Publisher** for the exact definition. The cross-check surfaces any divergence — never a silent wrong answer. **LIVE-CERT GATE.** |
| 3 | minor | Collision-shadowed record's `supersedes` edge was lost (authoring vs resolved layers could contradict). | Supersedes edges collected from all `eligible` records; ineligible records still excluded (verified). |
| 4 | minor | Version-skew abstain still emitted meaningless cross-version divergence lists. | Lists blanked under `version_skew`; `matches` False. |
| 5 | minor | Duplicate resolved `material_id` → nondeterministic map / silent dedup. | `duplicate_resolved_ids` flagged (forces `matches` False); deterministic maps. |
| R2 | minor | Fix #5's `sorted(mine)`/`sorted(theirs)` reintroduced the None-in-sort crash at the material_id level. | ALL 11 sorts made None-safe (str-keyed); grep-audited exhaustively. |

Round 2 confirmed #1/#3/#4 and the version-pin fail-fast hold, matching integrity preserved, identifiers-only
intact, no regression.

## 4. Tests
`tests/test_materials_resolution.py` (24) — cascade (inheritance / retirement / edition-eligibility-during-union
/ most-specific-on-collision / explicit + ineligible-never-suppresses supersession / approved-only terminal);
cross-check (matches / only_scout / only_publisher / file-revision mismatch / version-skew abstain / dup-id);
authoring invariants; version-pin fail-fast; None-id + None-file no-crash; tolerant wrapper; determinism;
identifiers-only. Full suite **425**.

## 5. Offline-certified; LIVE cert GATED on two Publisher confirmations
The module is offline-certified and **inert** (nothing invokes it yet — Phase-B S3 read + wiring is deferred,
as the delta family's Phase B was). Before the live cert against `edenseek-scout`:
1. **`rank_aware_explicit_supersession` definition** — so Scout's mirror matches the Publisher resolver's
   actual semantic (else a divergence is ambiguous: real Publisher issue vs Scout mis-model). Raised on the
   bridge (`responses/2026-08-07_atlas_to_johnny_rank_aware_supersession_semantic.md`). On the current
   `resolved_materials.json` (2 approved records, no supersession) the two agree regardless.
2. **The `material_index.json` wrapper shape** — the record + `resolved_materials` shapes are exact; the index
   file's top-level structure is not. Reader is tolerant (`records`/`materials`/`entries`); confirm the exact
   wrapper for the precise S3 read.

## 6. Certification statement
Additive standalone module; deterministic; references/identifiers only (no material text — verified);
mirror-not-import + version-pinned per ADR-0001; the `rank_aware` assumption is explicitly surfaced, not
silently assumed. **Offline-certified.** Remaining: Publisher confirms rank_aware + the index wrapper → Phase-B
read path → coordinated live cert (Scout's mirror vs the live `resolved_materials.json`, Publisher verifies from
`edenseek-scout`, same drill as Track B).
