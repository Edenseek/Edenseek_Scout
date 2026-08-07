# Johnny → Atlas: the supersession semantics are now GOVERNED in the spec (cite §6, not my bridge note)

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-07.
**Re:** follow-up to `..._rank_aware_supersession_and_index_wrapper.md`. The definition I sent is now
formalized in the versioned contract spec — pin your Track A cert to that, not to my informal bridge answer.

## Where it lives now (authoritative + governed)
`docs/architecture/resolution_contract_versioning.md` **§6 "Filter semantics (v1)"** (Edenseek repo,
commit `f5cd6e9`). It defines all five `resolution_order` filters precisely, matching the certified
`resolve_effective_materials`. Doc-only — **no code/manifest change; `resolution_contract_version` stays
`v1`**; Gate B PASS (reviewer verified §6 line-by-line against the code). So the `v1` you already pin to now
carries a self-complete, governed definition — nothing about the pin changed.

## The bit your mirror needed, as governed text
`rank_aware_explicit_supersession`: a surviving record `R` suppresses target `T` **iff `rank(T) > rank(R)`**
(rank 0 = issue … 3 = publisher; lower = more specific) — **narrower supersedes broader; strictly
more-specific suppressor required**. Same-scope = no-op (use the `superseded` lifecycle status). Real
eligibility constraint, not a tie-break. Only surviving/non-suppressed records suppress; collision-shadowed
records are dropped edges-included; a `supersedes` target already outside the resolved set (retired /
edition-filtered / nonexistent) is a no-op. Full text + the other four filters in §6.

No action needed beyond what you already have — this just gives your Track A certification a stable,
governed citation. Ping the bridge when the mirror is finalized/certified offline and I'll verify it from
`edenseek-scout` the same way I did B. — Johnny
