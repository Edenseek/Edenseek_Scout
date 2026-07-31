# Deployment & Live-Certification Plan — Metadata Accuracy v2

**Branch:** `week11-metadata-provenance-v2` → `main`
**Discipline:** deploy and activate/live-cert are SEPARATE, explicit steps.

## Preconditions
- [x] Offline certification complete (CERTIFICATION_REPORT.md), full suite green (353).
- [x] Adversarial review complete, findings resolved (§7 of the cert report).
- [ ] Publisher enhancement `5da0532` is the source of the *next* generated revision (fields appear only on
      generations after it ships — existing certified revisions carry neither).

## Step 1 — Merge & deploy (code only; no behavior change on legacy data)
1. Merge branch to `main`, push.
2. On the Oracle VM: `git pull` → `sudo systemctl restart edenseek-scout`.
3. Confirm `SCOUT_RUNTIME_MODE=production` is set (ADR-0002 boundary) BEFORE the new code serves.
4. Health check `/health`; confirm no scheduler errors.

**Safety:** on all legacy revisions (no provenance fields) v2 is numerically identical to v1, so a deploy
alone changes no existing number. The new metric only diverges once a revision carries real flags.

## Step 2 — Reply on the bridge (adapter ready)
Post `publisher_bridge/responses/2026-07-31_scout_adapter_v2_ready.md`: adapter **tolerates + reads** the new
sibling keys (no marker needed), `v1→v2` rationale, ready for the coordinated live cert.

## Step 3 — Coordinated live certification (the joint gate)
Sequence agreed with the Publisher (their `..._shipped_field_shapes.md`, D-5):
1. Publisher runs a fresh **generate-then-approve** publication on Society of Killers Issue 1, carrying
   `generation_provenance` + `metadata_generation_provenance`.
2. Scout audits that revision. Verify from `edenseek-scout`:
   - `metadata_model` / `metadata_prompt_version` / `metadata_prompt_sha256` axes are **populated** (not null);
     `provenance_source = per_output_fresh`.
   - `metadata_accuracy.denominator_basis = fresh_generated_outputs_only`; `disposition_coverage = all`.
   - Any `preserved_*` artifact appears in `excluded_preserved_artifacts` and is absent from the denominator.
   - A `metadata_comparability_key` distinct from the v1 series (methodology boundary), and a fresh `run_id`
     (no reconciliation to a stale run).
3. Both sessions confirm the numbers from the persisted report.

## Step 4 — Re-audit of `rev_0be8dc34` (regression proof, optional but recommended)
Re-audit the existing certified revision under v2; confirm acceptance reproduces **96.4%** (backward-identical
property, live-verified). Because the axis/fingerprint changed, this yields a NEW v2 run alongside the v1 one
— expected; the two are a methodology boundary, not a duplicate.

## Rollback
Revert the merge commit on `main`, `git pull` + restart on the VM. No data migration is involved (additive
read path; no persisted-schema change on Scout's side). Existing persisted reports are immutable and remain
valid under their own stamped versions.

## Post-cert
- Update memory + `MEMORY.md` (interface certified stable).
- Deliverables to founder: validation summary, emitted field contract, adapter changes, lessons learned,
  stability recommendation for the remainder of Week 11.
