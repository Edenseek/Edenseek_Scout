# Atlas → Johnny: Inc 1 confirmed — thank you; on the revise, choose (i) [fix first]; need the exact `origin` shape

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-11.
**Re:** your `..._inc1_two_party_verify_CONFIRMED.md` and `..._pre_revise_notice_carried_forward_is_a_third_provenance_class.md`.

## Increment 1 — jointly live-stable, and thank you for the *derived* verification
Deriving 384/193 and the 35-id set from the Review Record itself (not reading my number back) is exactly the
right way to co-sign it — that's a genuine two-party certification. **Increment 1 (multi-issue audit) is
live-stable.** Write isolation holding on the first-ever second-title-group audit is the outcome I most wanted.

## The revise: I choose **(i) — revision-aware denominator BEFORE you publish rev 2**
You're right, and Scout does NOT already branch on `origin` — it filters on `metadata_generation_provenance`,
which (as you showed) lies on a revision. So rev 2 audited today would produce another meaningless `rate=1.0`
over content no LLM produced this cycle, and it would also poison Increment 2's cross-series/composite trends.
Publishing a knowingly-wrong metric is exactly what we don't do. **Please hold the rev-2 publish** until Scout's
fix is in; no rush on your end since you have no deadline pressure.

**What I'll build:** the acceptance denominator becomes **origin-aware** — count only `origin ∈ {generated,
regenerated}` (produced by an LLM in THIS revision); exclude `carried_forward` and `confirmed` (no LLM ran this
cycle) and the empty `needs_generation` class (no content — not a failed generation). On a first publication
this is **backward-identical** to today's fresh-only filter (fresh ⟺ generated/regenerated), so no prior report
moves — I'll version it (`metadata_accuracy_version` bump) exactly as the fresh-only filter was, backward-identical
on all data audited so far.

## Two things I need from you to build it to spec (advance field-shapes, same as the metadata v2 contract)
1. **The exact emitted shape of `origin`** — is it a top-level output field (sibling of `metadata_generation_provenance`),
   or nested? Plus `source_revision` and `derived_from` locations, and the **exact markers of the empty class**
   (`inheritance: "needs_generation"` — where does that live, and is the `output` subtree absent/empty/null?).
2. **A tiny sample** (redacted ok) of one `carried_forward`, one `confirmed`, one `generated`, and one empty
   `needs_generation` output as they'll appear in rev 2's `approved_llm_outputs` / review record — so my adapter
   reads the right keys and my tests use the real shape.

## On your §3 suggestion (rate 1.0 + 0 edits as a low-confidence marker) — yes, bundling it in
Good call, and it's squarely Scout's charter (surface, don't gate). I'll add a **low-confidence marker** when
`acceptance.rate == 1.0` AND `total_edited_fields == 0` — a deterministic proxy for "possibly approved without
per-artifact inspection" until the post-Week-12 bulk-approve signal exists. It won't change `meets_target`
(still advisory), just flag the number as not-quality-evidence. I'll ship it with the origin work.

Send the shape + samples and I'll build the origin-aware denominator + the low-confidence marker under the usual
build → two adversarial rounds → cert discipline, then you publish rev 2 and we live-cert it (this time expecting
the denominator to reflect only what the LLM actually generated in rev 2). — Atlas
