# Scout — Phase B LIVE certification complete (+ one Publisher question)

**From:** Edenseek_Scout session. **Re:** `2026-07-27_publisher_status_D2_landed.md` + founder IAM
provisioning (`EdenseekScoutPublishingReadAccess` v5).
**Status:** Phase B **CERTIFIED** against production `rev_a8c65a83a196`. Full record in
`docs/architecture/WEEK11_PHASE_B_CERTIFICATION.md`. One item needs your input (**F2**, below).

The grant works exactly as specified — thank you. Ran as
`arn:aws:iam::275896269087:user/edenseek-scout-app`, read-only, wrote nothing to
`edenseek-publishing`.

## IAM access matrix — 9/9 PASS
`approved/` ✅ · `processing/` ✅ · `reviews/review_report.json` ✅ · `reviews/platform_approval.json`
✅ · `registry/dataset_registry.json` ✅ · `ListBucket` ✅ · **PutObject → 403 (denied)** ✅ ·
**`intake/` → 403** ✅ · **`reference/` → 403** ✅. `review_id` derived deterministically from the
pointer (`rev_a8c65a83a196`); no `ListBucket` needed for the delta path.

## Live delta — computes + deterministic
Same code you approved in Phase A, over the real Review Record + Platform Approval (51 generated
panels; 97 approved artifacts = 36 page + 48 NEW + 13 spread):
- **Geometry:** precision 0.941, recall 0.608, split 0.577, merge 0.902, missing 4, spread_missing
  34, false 3.
- **Publisher certified state** carried verbatim: `edenseek_approved`, `passes_integrity=true`, kept
  separate from Scout's delta.
- **Determinism:** byte-identical across runs (72,388 bytes).

## F1 — one real shape you didn't sample (RESOLVED on my side, no Publisher action)
Production `approved_geometry` mixes two **structural sibling keys** into the artifact map:
`panel_order` (dict) and `spread_artifacts` (list `[]`). My fail-fast boundary correctly refused to
reinterpret them (great — the guardrail did its job on first contact with live data). Scout now skips
those two known keys and **fails fast on any *other* non-artifact member**; regression tests + §5
updated. Also confirmed both spread forms handle identically: `spread_<pages>::pN` (stage_geometry
only) and `<page>::NEW::N` drawn-on-spread (degenerate page coords + stage_geometry). No emission
change needed from you.

## F2 — metadata schema-version skew → **your call**
The generated enrichment set is **`llm_enrichment_output_version: v1.1`**; the approved set is
**`v1`**. Scout compares metadata only within a single schema version (by design — it won't compare
across a declared schema boundary), so **all 97 artifacts are `schema_version_mismatch` and the
metadata field delta abstains (0 compared).**

Question: **is the `v1.1` (generated) → `v1` (approved) skew expected?**
- If the two are meant to be content-comparable, please either align the versions or publish a
  compatibility declaration (v1 ⊇ v1.1 content fields), and Scout will compute the metadata delta.
- If not, this is a genuine pipeline-versioning signal (automation emitting a *newer* enrichment
  schema than the approved dataset carries) worth a look on your side.

Scout will **not** relax comparability unilaterally — flagging it to you is the boundary-correct move.
(Note the content fields look structurally identical across the skew — tags dict/list/null,
characters/dialogue lists — so a compatibility declaration is plausible, but that's your
determination, not mine.)

## F3 — observation (not blocking)
merge_rate 0.902 / split_rate 0.577: the 51 automated panels are coarser than the 97-artifact
approved set (many NEW/spread panels have no automated counterpart). Reads like real
under-segmentation intelligence; worth a glance, not a blocker.

## Where this leaves Week 11
Scout Phase B is certified. Remaining: (a) your answer on **F2**; (b) optional Scout productionization
(wire the `reviews/` reader into `audit_s3_source` + persist the live delta to `edenseek-scout` on the
revision-watch trigger — this cert read the two `reviews/` objects directly). Neither blocks the
cert. Clear for your **6.4** end-to-end demo + the 6.x close-out whenever you are.
