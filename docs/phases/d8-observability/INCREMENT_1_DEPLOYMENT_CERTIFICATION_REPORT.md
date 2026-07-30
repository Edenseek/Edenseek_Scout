# D8 Increment 1 — Deployment Certification Report

> Execution of `INCREMENT_1_DEPLOYMENT_VALIDATION_PLAN.md`. **Result: PASS — D8 Increment 1
> (`/observability/health`, Issue Health) is CERTIFIED IN PRODUCTION.** Additive, read-only, reversible;
> no existing behavior changed; no Publisher writes.
>
> - Date: 2026-07-30. **Deployed:** `main` `4857ed2` (D8 code = merge `f7952b8`; `4857ed2` adds the D8 docs).
>   VM fast-forwarded from `b817270` → `4857ed2`; service restarted, active.
> - **Rollback point:** `b817270`. Change vs the prior running deployment = **D8 Increment 1 only**
>   (additive `scout_observability.py` + one `app.py` route; everything else docs).
> - Evidence: operator captures on the live VM + independent engineering-session corroboration
>   (endpoint before/after + read-only S3).

## Validation matrix

| # | Check | Expected | Operator | Independent (session) | Result |
|---|-------|----------|----------|-----------------------|--------|
| 1 | Dashboard / `/health` | 200 | `{"status":"online"}` | `/health` → 200 | ✅ |
| 2 | `/observability/health` (no-auth) | 404 → **401** | 401 | pre-deploy 404 → **401** | ✅ |
| 2 | `/observability/health` (authed) | `summary {healthy:1,attention:0,unknown:0,total:1}`, `issue_001` healthy | matches | **recomputed from live Registry == operator body** | ✅ |
| 3 | `/registry` (no-auth) | 401 (unchanged) | 401 | 401 | ✅ |
| 3 | `/registry` (authed) | unchanged: count 1, `generated_at 20:31:24.802Z`, fp `2f6f9dbd…` | count 1, same `generated_at` | S3 fp `2f6f9dbd…` (invariant) | ✅ |
| 3 | `app.py` handler diff | `/registry` byte-for-byte unchanged | — | `git diff 69bcae5 f7952b8` = D8 additions only | ✅ |
| 4 | `/registry/tree` (authed) | hierarchy intact | intact (`edenseek→…→issue_001`) | tree_view over S3 Registry identical | ✅ |
| 5 | Scheduler continuity | job re-registers post-restart | `20:50:24 Registered Registry rebuild job (every 60 min)` | Registry `generated_at` unchanged since deploy (next run ~21:50, as expected) | ✅ |
| 6 | No Publisher writes / boundary | writes only `edenseek-scout` | no errors/tracebacks/failed jobs | Registry fp invariant; no rebuild fired during deploy; IAM Deny holds | ✅ |

## Notes
- **Endpoint cross-check:** the engineering session independently recomputed `issue_health` from the live
  `registry/registry.json` and got `summary {healthy:1, attention:0, unknown:0, total:1}` / `issue_001 =
  healthy` — **identical** to the operator's authed `/observability/health` body. (This also resolves a
  cosmetic copy/paste truncation in the operator's item-3 summary; the correct `total` is `1`.)
- **Boundary:** the Registry logical fingerprint (`2f6f9dbd…`) is unchanged before/after; D8 introduced no
  new write and no Publisher access; the scheduled Registry rebuild remains the only writer, to
  `edenseek-scout` only.
- **Scheduler:** re-registered cleanly at restart (every 60 min); the next scheduled rebuild is due ~21:50
  (60 min after the `20:50` re-registration) — continuity preserved.

## Verdict
**D8 Increment 1 is CERTIFIED IN PRODUCTION.** The deployment was additive and reversible: `/health`, the
existing authed `/registry` + `/registry/tree`, authentication, the Registry, and the scheduler are all
unchanged; the new read-only advisory `/observability/health` projection is live and correct against the
live Registry; no Publisher writes. **Production baseline: `4857ed2`.** Rollback: `git checkout b817270` +
restart (code-only, immediate).

*This certified production baseline is the foundation for D8 Increment 2 (Series / Publisher Health rollups,
reusing `roll_up`).*
