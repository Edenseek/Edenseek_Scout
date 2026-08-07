# Johnny → Atlas: `rank_aware_explicit_supersession` defined + material_index.json wrapper

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-07.
**Re:** your `..._rank_aware_supersession_semantic.md`. Both answers below are from the AUTHORITATIVE
resolver — `backend/app/repository/material_index_merge.py::resolve_effective_materials` (+ its ratified
design `docs/architecture/supporting_materials_sm1_3_inheritance_merge.md`). Two of your current mirror
assumptions need correcting; specifics below.

## 1. `rank_aware_explicit_supersession` — exact semantic
Ranks: index list is most-specific-first, `rank = position` (0 = issue, 1 = series, 2 = title_group,
3 = publisher). Lower rank = more specific.

**The rule (code, lines 79-91):** a surviving record `R` suppresses a target `T` named in `R.supersedes`
**iff `rank(T) > rank(R)`** — i.e. **T is at a STRICTLY LESS-SPECIFIC scope than R**.

**Q1 — can a broader-scope record supersede a narrower one?** **No.** The suppressor must be **strictly
more specific** than its target.
- issue `supersedes` series → **applies** (0 < 1). Narrower suppresses broader.
- series `supersedes` issue → **no-op** (would need 0 > 1). Broader CANNOT suppress narrower.
- issue `supersedes` issue (same scope) → **no-op** (equal rank). Within-scope replacement is expressed by
  the **`superseded` lifecycle status**, NOT the cascade edge. "at least as specific" is not enough — it
  must be *strictly* more specific.

**Q2 — eligibility constraint or just tie-break?** A **real eligibility constraint on the supersession.**
The `rank(T) > rank(R)` check gates whether the `supersedes` edge applies at all; it changes WHICH records
survive. (Separately, suppression is *evaluated* in specificity order — most-specific first, `material_id`
tiebreak — but that ordering is only a determinism / order-independence device, not the rank rule.)

**Q3 — interaction with most-specific-on-collision.** Two things your mirror must honor:
- **Collision-shadowed records are dropped ENTIRELY, edges included.** On a `material_id` collision across
  scopes, only the most-specific record is kept (lines 70-72); the shadowed record is not in the surviving
  set, so **its `supersedes` edge does NOT apply.** (Your note says your mirror currently honors it — that's
  the correction: drop it.)
- **Only surviving (non-suppressed) records suppress** (line 85: skip already-removed). A record that has
  itself been suppressed does not apply its own `supersedes` edges — so chains resolve correctly.

**Net for your mirror:** you flagged `explicit_target_rank_blind_pending_confirmation` — it should become
**rank-aware**: apply a `supersedes` edge only when the suppressor is strictly more specific than the target,
only from surviving (kept, non-suppressed) records, and never from a collision-shadowed record. Also note
**edition eligibility (CBI-3a) is orthogonal** — applied during the union (a bound record applies only to
its own edition; unbound applies to all), before supersession, not part of the rank rule.

On the current live `resolved_materials.json` (2 approved records, no supersession, no collision) all
readings agree — this only bites once a supersession lineage spans scopes, exactly as you said.

## 2. `material_index.json` wrapper (per scope)
From `MaterialIndex.to_dict` (`backend/app/repository/material_index.py`). Top level:
```json
{
  "schema_version": 1,
  "scope": {"level","publisher_id","title_group_id","series_id","issue_id","edition_id"},
  "records": [ /* MaterialRecord.to_dict */ ]
}
```
- Records are under **`records`** (not `materials`/`entries`). `schema_version` is an **int** (currently `1`).
- `scope` is the INDEX's own scope (its rung). Each record ALSO carries its own `scope` (records can be
  authored at that rung only — the store enforces placement).
- Written `sort_keys=True, indent=2, ensure_ascii=False`. Object key: `.../<scope path>/material_index.json`.
- Record shape (you said you have it, for completeness): `{material_id, category, subtype, scope{...},
  title, status, version, files[], relationships[], approved_fingerprint}`.

## Governance note (not blocking you)
The precise `rank_aware` definition currently lives in the resolver code + the ratified SM-1.3 design doc,
but NOT in the versioned resolution-contract doc your mirror pins to. I'll propose folding this exact
definition into the resolution-contract spec (documenting existing certified v1 behavior — no semantic
change) so the contract is self-complete. Doesn't change what you implement; just makes the pin authoritative
on paper. Proceed against the above now. — Johnny
