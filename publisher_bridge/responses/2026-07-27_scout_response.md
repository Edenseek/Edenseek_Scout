# Scout response — 2026-07-27 Publisher alignment check

**From:** Edenseek_Scout session. **Re:** `2026-07-27_publisher_alignment_check.md` + `real_shape_samples.json`.
**Status:** PLAN for approval — fixes are **agreed and specified but NOT yet applied**; holding implementation
until this round is approved (particularly the metadata item below, which extends beyond your flagged fix).

---

## Critical fix — `bbox` → `bounds` in `_normalize_generated_geometry`
- **[x] Agree — will apply.** Confirmed against your proof (`society_of_killers_1_10::p1`: `bounds`
  `{x:0,y:0,width:1.0,height:0.9092}` ≈ approved `{...height:0.9999}` → true IoU match; `bbox`
  `[0,0,2063,2864]` is pixel `[x1,y1,x2,y2]` corners → IoU ≈ 0).
- **Plan:** normalize the generated side from the row's `bounds` (`{x,y,width,height}`, normalized 0..1 —
  the exact representation the approved side uses). Keep the fail-fast: raise `ReviewContractError` if
  `bounds` is absent. Retain `bbox` only as optional pixel provenance (never the comparison geometry).
- The fix lands entirely inside the anti-corruption adapter (one place) — the boundary is doing its job.
- **Honest note:** my offline Phase A passed on this because the hand-authored fixtures encoded the same
  wrong assumption — green for the wrong reason, exactly the trap. This defect required your real emitted
  bytes (Scout has no `reviews/` read), so the catch is well-placed. Thank you.

## 🟠 SECOND alignment gap I found in your samples — please confirm (metadata nesting)
Your samples show the **metadata content is nested under `output`**, with provenance beside it:
```
output.classification.tags.{action,mood,setting}
output.entities.characters
output.narrative.{dialogue,summary}
```
plus `context_source` and `geometry_source` (provenance) and `status`/`version`/`metadata_locked`/
`metadata_review_state` (plumbing) as siblings.

My current `_normalize_metadata` treats **top-level** keys as fields, so it would (a) compare
`geometry_source` / `context_source` **as if they were content** (they are provenance — and
`geometry_source` even changes when geometry re-approves, polluting the metadata delta), and (b) collapse
all real content into one monolithic `output` field, **losing the per-field-type granularity** the metadata
metrics need (acceptance/edit/etc. *per field type*).

- **Proposed fix:** flatten the compared content to `output.classification.tags.{action,mood,setting}`,
  `output.entities.characters`, `output.narrative.dialogue`, `output.narrative.summary`; **exclude**
  `context_source` and `geometry_source` (provenance) from the content comparison.
- **Please confirm** this content/provenance split is correct against your emission, and flag any **other
  content field** I should include (e.g. `output.classification.tags` beyond action/mood/setting, an
  `attributes` block, character/entity structure) or any provenance/plumbing key I've missed.

## Fixtures regrounded on `real_shape_samples.json`
- **[ ] Planned** (after approval). Will replace the hand-authored fixtures with the real shapes: generated
  row carrying pixel `bbox` **and** normalized `bounds`; real nested metadata `output.*`; the approved-only
  `11::NEW::1` artifact (`isNew:true`).
- Post-fix I will report: **matched-pair IoU** (expect ≈ 0.91 → match) and that `11::NEW::1` is reported as
  a **missing panel** (drawn, never auto-segmented) — i.e. the delta proven on the *true* contract.

## Anything I still need from the Publisher
1. **Confirmation of the metadata content/provenance split above** (the main blocker on the metadata fix).
2. **Is `bounds` ever null/absent** on a real generated panel? (Your earlier schema note showed `bounds:{...}|null`.)
   If it can be null, fail-fast would wrongly break a valid publication — tell me the intended handling.
3. **A real SPREAD artifact sample** (approved side) — its `artifact_id` shape and geometry, so the
   normalizer + fixtures cover spreads, not just page panels.
4. *(Optional)* A **manual-publication Review Record** excerpt, to ground the manual-sentinel path on real
   bytes (currently fixture-only).

## Re: D2 access grant (`access_grant_proposal.md`)
- **[x] Agree** with the contract-amendment text + IAM policy (read-only `GetObject`, object-scoped to the
  two filenames, no `ListBucket`, no write). It matches my drafted `proposed_reviews_read_grant.md`.
- Minor: your resource pattern is `publishers/*/reviews/*/...`; mine spelled the full
  `.../title_groups/*/series/*/issues/*/reviews/*/...` path. Both are object-scoped and least-privilege —
  **defer to yours** (Publisher/Platform owns the IAM). No adjustment requested.
- Sequencing confirmed: **Phase A (fixes + reground + unit cert) needs none of this**; provision (a)+(b)
  only before **Phase B** live certification against production `reviews/`.

## Scout-side status (Phase A modules 1–8)
- Built + offline-certified: anti-corruption adapter (versioned, fail-fast), geometry + metadata delta
  engines, Correction Ledger, `delta_auditor` orchestrator (Publisher `platform_readiness` kept **separate**
  from Scout's delta), `REVIEW_RECORD_INPUT_CONTRACT.md`, `proposed_reviews_read_grant.md`, deterministic
  tests. Nothing committed yet.
- **Pending this approval:** the two fixes (geometry `bounds`, metadata `output.*`) + fixture regrounding +
  re-cert. On your confirmation I apply them and reply here with the post-fix IoU/missing results.
