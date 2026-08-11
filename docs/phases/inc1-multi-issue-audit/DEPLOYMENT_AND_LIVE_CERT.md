# Increment 1 — Multi-Issue Audit: Deployment & Live-Cert Plan

**Branch:** `week12-inc1-multi-issue-audit` → `main`
**Discipline:** deploy and live-cert are SEPARATE, explicit steps. Gated on the offline cert (2 adversarial
rounds) completing first.

## Preconditions
- [ ] Offline cert complete (adversarial rounds resolved), full suite green.
- [ ] Johnny's expansion approval on file (received 2026-08-11) — read footprint confirmed bucket-wide.

## Step 1 — Merge & deploy (backward-safe)
1. Merge branch to `main`, push.
2. On the Oracle VM: `git pull` → `sudo systemctl restart edenseek-scout`.
3. Confirm `SCOUT_RUNTIME_MODE=production` set (ADR-0002) BEFORE the new code serves.
4. `/health` green; no scheduler errors.

**Safety:** additive. The single-issue path (`/run-delta-audit`, the env-configured prefix) is unchanged;
`audit_all_discovered` is a new, separately-triggered entry point. Nothing runs multi-issue until explicitly
invoked (`--all` / `/run-delta-audit-all`); the scheduler is untouched (its activation is Increment 4).

## Step 2 — Run the multi-issue audit (VM / online)
Two equivalent triggers:
- **Online (preferred, matches how the founder runs audits):** `POST /run-delta-audit-all` from the dashboard/
  authenticated client.
- **VM shell:** `python scout_delta_audit.py --all` (same env as the service: `SCOUT_RUNTIME_MODE=production`
  + AWS creds).

Expected: Discovery enumerates the currently-published issues (today: `society_of_killers` #1 and
`i_ride_for_them` #1; `egypt_the_cat` is unpublished → not discovered). The result is
`{discovered, counts, results:[per-issue]}`.

## Step 3 — Verify from `edenseek-scout` (the multi-issue proof)
1. **Both issues audited:** the result `results[]` has an entry per discovered issue, each `persisted` (fresh)
   or `skipped`/`reconciled` (already current). `society_of_killers` #1 should be `skipped` (already at
   run_seq ≥ 10) and `i_ride_for_them` #1 `persisted` (first audit).
2. **Per-issue write isolation:** a `scout_delta_report_*` now exists under **`i_ride_for_them`'s** own issue
   prefix in `edenseek-scout`, and `society_of_killers`'s reports/index/ledger are unchanged (not clobbered).
3. **⭐ The mixed-provenance checkpoint (`i_ride_for_them` #1, joint with Johnny):** on its delta report,
   `metadata_benchmark.metadata_accuracy`:
   - `acceptance.denominator` reflects the **65 fresh** outputs, NOT 100;
   - `excluded_preserved_artifacts` lists the **35 `preserved_approved`** artifacts;
   - `disposition_coverage = "all"` (every output flagged).
   This is the first real live exercise of the fresh-only filter — Johnny verifies it from raw `edenseek-scout`,
   same as Track B.
4. **Per-issue idempotency:** re-running `--all` re-audits nothing already current (all `skipped`/`reconciled`).

## Step 4 — Report to the bridge
Post the result: both issues audited, write-isolation confirmed, and the mixed-provenance checkpoint numbers,
for Johnny's independent `edenseek-scout` verification → jointly mark Increment 1 live-stable.

## Rollback
Revert the merge on `main`, `git pull` + restart. No data migration; per-issue reports are immutable and
independently valid. The single-issue path is unaffected either way.

## Scope boundary (so results aren't over-read)
Increment 1 produces per-issue **audit data**. It does NOT yet surface series/cross-series/composite views —
that's **Increment 2** (Registry rebuild over all issues + intelligence aggregation + dashboard). After Inc 1,
the existing `rebuild_discovered` (Registry) can be run to reflect all issues in the observability projections,
but wiring that into the refresh + the dashboard views is Inc 2.
