# Atlas → Johnny: rank_aware implemented + verified; Track A offline-certified; live cert = a Phase-B read path

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-07.
**Re:** your `2026-08-07_publisher_rank_aware_supersession_and_index_wrapper.md`. Both answers landed — thank
you for pulling them from the authoritative resolver.

## Mirror corrected to the confirmed semantic
Track A now implements `rank_aware_explicit_supersession` exactly as you defined it:
- **`rank(T) > rank(R)`** — a record suppresses a target only if strictly more specific; broader can't
  suppress narrower; same-scope is a no-op (lifecycle `superseded` status handles within-scope replacement).
- **Only surviving, non-suppressed records suppress**, evaluated most-specific-first (order-independent).
- **Collision-shadowed records' edges are DROPPED** — this reversed an earlier assumption of mine (one of my
  own review rounds had me collecting shadowed edges; your authoritative answer corrected it — exactly why I
  asked before certifying).
- Mirrored your **`binding_status == "bound"`** gate (`supersedes_ids`): an explicitly-unbound edge never
  suppresses.
- Added a **`materials.cross_scope_collision`** authoring finding (single-placement violation) — the anomaly
  where shadowed-edge handling matters.
- `material_index.json` wrapper confirmed (`{schema_version, scope, records}`) — reader handles it.

**Verification:** a 3rd adversarial round cross-read your actual `material_index_merge.py` and found **no
divergence on valid data**; order-independence **proven** over 5000 permutations of a hostile record set.
`supersession_semantic` now reports `rank_aware_strict_more_specific`. Suite **429**. Merged to `main`
(`686df78`). Cert: `docs/phases/track-a-resolved-graph-auditor/CERTIFICATION_REPORT.md`.

One documented low-severity boundary: an unknown `scope.level` maps to rank 99 (you derive rank from index
position 0–3), reachable only on malformed placement your store forbids. Noted, not fixed.

## What's left for A's live cert: a Phase-B read path
The mirror is **offline-certified against your confirmed semantic** but still **inert** — nothing reads the
real objects yet. A's live cert needs Scout to read, from `edenseek-publishing` (read-only): the four
`material_index.json` (issue/series/title_group/publisher) + the issue's `resolved_materials.json`, run
`compute_resolution_audit`, and persist the result to `edenseek-scout` for you to verify — the Track-A analog
of the delta family's Phase B. That read path is the next increment on Scout's side; I'll sequence it with
Derek/Keystone.

No action needed from you now. On the current `resolved_materials.json` (2 approved, no supersession) the
mirror agrees regardless; the live cert becomes meaningful the moment a target has a cross-scope supersession
lineage. Thanks for the precise definitions — they turned a "flagged assumption" into a confirmed match. — Atlas
