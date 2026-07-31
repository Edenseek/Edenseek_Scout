# Certification report — geometry correctness (Inc 1–3) + runtime safety boundary

> Branch `geometry-correctness-and-runtime-safeguard` (7 commits, `422acac`…`9df8d2e`).
> **Verdict: PASS.** Certified for deployment; deployment is a separate operational step
> (`DEPLOYMENT_PLAN.md`), gated on founder approval and `SCOUT_RUNTIME_MODE=production` on the VM.

## Scope certified
- **Runtime safety boundary** (ADR-0002): `scout_runtime.py` gate on the only two real S3 client
  factories; deny-by-default; test processes always refused.
- **Geometry correctness (Inc 1–3)**: page-scoped matching (fixes cross-page inflation) +
  spread-to-spread matching (stratified page/spread/total) + quality-weighted
  `segmentation_accuracy = E/(A+FP)` + per-panel resize diagnostics. `GEOMETRY_MATCH_VERSION` → `v2`.

## Certification activities + evidence
- **Full test suite:** 341 tests, **0 failures**, under both discovery styles (`-s tests`
  deny-by-default and `-t .` test-mode) — verified the boundary holds regardless of launcher.
- **Determinism:** the delta serializes byte-identically across repeated runs on live
  `rev_0be8dc34` (all iteration over `sorted(...)`; order-stable concatenation).
- **Internal invariants (checked on live data):** total = page + spread exactly (gen/appr/false);
  `segmentation_accuracy.denominator == A + FP`; earned credit `E ≤ matched_approved ≤ n_app`
  (so `score ≤ 1`); no cross-stratum double-counting (page/spread disjoint by `is_spread`).
- **Boundary:** read-only against `edenseek-publishing`; the guarded factories are the only
  `boto3.client` sites; the incident path (`audit_current_revision` with no client) is refused in
  a non-production/test context.
- **Independent adversarial (hostile) review:** ran over the geometry math, scoping, adapter edge
  cases, consumer contracts, and the safety boundary — findings below, all resolved.

## Hostile-review findings — all resolved (commit `9df8d2e`)
| # | Sev | Finding | Resolution |
|---|---|---|---|
| 1 | MED | Over-segmented/duplicate output scored a false `1.0` (invariant violated) | `FP = n_gen − credited` (false **+** over-seg excess); regression test added. Live unchanged (excess=0). |
| 2 | MED | One non-numeric page id (`cover…`) aborted the **whole** issue delta | `_derive_page_number` falls back to a string page scope; regression test added. |
| 3 | MED | Generated spreads derived a page number; approved didn't (asymmetry + abort risk) | Generated spreads skip derivation — symmetric. |
| 4 | MED | `page_range`-less spreads could collapse to one scope and falsely match | Spread scope falls back to `artifact_id`; entries now carry it. |
| 5 | LOW-MED | "Test mode" was launcher-conditional; a stray `SCOUT_ALLOW_REAL_S3` could leak | Guard refuses a real client whenever a unit-test runner is loaded (app never imports it). Verified. |
| 6 | LOW | `SCOUT_REPORT_INDEX.md` documented old benchmark key names | Updated to the stratified `v2` shape. |

**Reviewer-confirmed OK:** consumer field contracts (`delta_ledger`, `audit_review`,
`scout_intelligence`, `scout_benchmark`) all resolve; micro-average math; division-by-zero guards;
determinism; cross-page/cross-spread scoping; single guarded choke point for S3 clients.

## Live result (certified numbers, `rev_0be8dc34`)
- Detection: precision 0.843 / recall 0.443 (page 0.946/0.556, spread 0.571/0.235).
- Quality-weighted accuracy `E/(A+FP)`: page 0.522, spread 0.173, **total 0.389** (target 0.95).
- Resize bias median 1.0 → the gap is **detection/recall, not box sizing**, worst on spreads.

## Deployment note
Deploying makes v2 present; the first v2 audit produces a fresh, corrected report as a clean new
`run_id` (v1 fingerprint ≠ v2). **Must** set `SCOUT_RUNTIME_MODE=production` on the VM first, or the
agent fail-safes (denies its own client). See `DEPLOYMENT_PLAN.md`.
