# D8 Increment 2 — Deployment Certification Report

> Execution of `INCREMENT_2_DEPLOYMENT_VALIDATION_PLAN.md`. **Result: PASS — D8 Increment 2 (Series &
> Publisher Health) is CERTIFIED IN PRODUCTION.** Additive, read-only, reversible; existing behavior
> unchanged; no Publisher writes; hierarchy coherence proven live.
>
> - Date: 2026-07-30. **Deployed:** `main` `fa95ba4` (D8 Inc 2 code = merge `615278e`; `fa95ba4` adds docs).
>   **Rollback point:** `4857ed2`.
> - Evidence: operator captures on the live VM + independent engineering-session corroboration (endpoint
>   before/after + read-only S3 recompute).

## Deployment note — initial discrepancy + resolution (certification process worked)
The first validation attempt returned **404** for the new endpoints. Diagnosis (from git history, no code
change): the 404s were the exact signature of `4857ed2` (D8 Inc 1) — the VM was **still running Inc 1**, not
`615278e`. The routes were confirmed present on `main`/`615278e` (merged, not "ahead"); no repository or
config change was warranted. The operator advanced the VM (`git pull --ff-only origin main` → `fa95ba4`) and
restarted; both endpoints became available immediately. **The discrepancy was an operational deployment
mismatch, not a code defect** — certification correctly halted, root cause was understood, the deployment
state was corrected, and production was re-validated.

## Validation matrix (post-correction)

| # | Check | Expected | Operator | Independent (session) | Result |
|---|-------|----------|----------|-----------------------|--------|
| 0 | Deployed revision | `615278e`+ | `fa95ba4` | routes present in `615278e`/main | ✅ |
| 1 | Existing endpoints byte-for-byte | unchanged | `/health` 200; `/observability/health` = Issue Health; `/registry`+`/registry/tree` unchanged | `/health` 200; `/observability/health`, `/registry` still 401 no-auth | ✅ |
| 2 | `/observability/health/series` | `society_of_killers = healthy`, `issue_counts {healthy:1}` | matches | recomputed from live Registry == body; **404 → 401** no-auth | ✅ |
| 3 | `/observability/health/publisher` | `edenseek = healthy`, `series_counts {healthy:1}` | matches | recomputed == body; **404 → 401** no-auth | ✅ |
| 4 | Registry fingerprint unchanged | `2f6f9dbd…` | — | S3 fp `2f6f9dbd…` (invariant) | ✅ |
| 5 | Scheduler continuity | re-registers post-restart | scheduler registered | Registry `generated_at 21:50:24Z` (last hourly run; no anomaly) | ✅ |
| 6 | No Publisher writes / boundary | writes only `edenseek-scout` | no tracebacks/failed jobs | fp invariant; only scheduler writes; IAM Deny holds | ✅ |
| 7 | **Coherence invariant** | `publisher == roll_up(series) == roll_up(all issues)` | healthy | **proven live: all == `healthy`** | ✅ |

## Notes
- **Endpoint cross-check:** the session independently recomputed `series_health` / `publisher_health` from
  the live `registry/registry.json` and matched the operator's authed bodies exactly
  (`society_of_killers = healthy`, `edenseek = healthy`, `issue_counts/series_counts {healthy:1}`).
- **Recompute-from-below verified in production:** Publisher Health equals the rollup of Series Health, which
  equals the rollup of Issue Health — the binding hierarchy invariant holds on live data.
- **Boundary:** the Registry logical fingerprint (`2f6f9dbd…`) is unchanged; D8 Inc 2 introduced no new
  write and no Publisher access; the scheduled Registry rebuild remains the only writer (to `edenseek-scout`).

## Verdict
**D8 Increment 2 is CERTIFIED IN PRODUCTION.** The deployment was additive and reversible: `/health`,
`/observability/health` (Issue Health), `/registry`, `/registry/tree`, authentication, the Registry, and the
scheduler are all unchanged; the new read-only advisory `/observability/health/series` + `/publisher`
projections are live, correct, and coherent with the layers beneath them; no Publisher writes. **Production
baseline: `fa95ba4`.** Rollback: `git checkout 4857ed2` + restart (code-only, immediate).

*This certified production baseline is the foundation for the next Health Projection level (Cross-Series
Health), under the same recompute-from-below discipline.*
