# Certification Report — SXI-2e (post-audit projection freshness)

**Track:** Scout Expansion Increment 2 · sub-increment **2e** (the freshness loop)
**Branch:** `week12-sxi2e-rebuild-freshness`
**Date:** 2026-08-12 · **Discipline:** certified-first (build → adversarial review → certify → deploy → verify)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for merge → deploy

---

## 1. What changed and why

The 2c/2d per-scope + series-comparison views (and the Registry-derived Health) read the persisted
projections that `rebuild_discovered` (Registry) and `rebuild_all` (benchmarks) write. Until those were
rebuilt after an audit, the views showed stale data or "—". SXI-2e closes the loop: the multi-issue `--all`
audit now refreshes the derived projections after the reports are persisted — **recompute-from-below** (P2).

## 2. Change

- `scout_delta_audit._rebuild_projections()` (new) — after a multi-issue audit, calls
  `scout_registry.rebuild_discovered()` then `scout_benchmark.rebuild_all(generated_at=<now>)`, each in its
  **own** try/except → recorded as `"rebuilt"` / `"failed: <Exc>"`. **Best-effort and NON-FATAL**: the
  immutable reports are already persisted, so a rebuild failure is recorded and never fails the audit; a
  registry failure does not block the benchmark rebuild. Called with **no client** so each rebuild
  self-resolves its correctly-regioned client (Registry: approved region for Discovery + scout region for
  persist; benchmark: scout region).
- `scout_delta_audit.audit_all_discovered(..., rebuild=False)` — when `True`, runs `_rebuild_projections()`
  after the per-issue loop and records the outcome under `result["rebuild"]`. **Default `False` preserves the
  certified Increment-1 behavior byte-for-byte.**
- The CLI `--all` and `POST /run-delta-audit-all` opt in with `rebuild=True`.

## 3. Safety / boundary

Read-and-advise preserved: the rebuilds read the Publisher repository GetObject-only (Discovery) and write
only `edenseek-scout` (Registry + benchmark projections) — the same surfaces the audit already writes, under
the same authorization; nothing new is written to Publisher data. The rebuild runs within the same `--all`
invocation, so it inherits the audit's runtime-safety context (ADR-0002). `generated_at` is a freshness
stamp only — it does not participate in benchmark comparability/idempotency (those key on the report
entries' comparability keys), so using wall-clock now (vs the old epoch default) changes no metric.

## 4. Tests

Full suite **486 passed** (+4, in `tests/test_multi_issue_audit.py`): `rebuild=True` refreshes both
projections (`result["rebuild"] == {registry: rebuilt, benchmark: rebuilt}`); default `rebuild=False` calls
neither and omits the key (Increment-1 behavior); a registry-rebuild failure is **non-fatal** — recorded as
`failed: …`, the benchmark rebuild still runs, and the audit counts stay intact; the endpoint opts in
(`rebuild=True`).

## 5. Adversarial review (one round + fold)

**Verdict: safe to merge + deploy — no MAJOR/MINOR correctness defect that breaks the guarantees.** The
reviewer confirmed: the non-fatal design holds (per-rebuild try/except; registry failure doesn't block
benchmark; the audit result is built before rebuild and only *added to*); backward-compat is byte-identical
(`rebuild=False` default; no scheduler/background caller); passing no client is the *correct* choice (the
audit's client is an approved-region read client; reusing it would misroute the scout-bucket writes);
`generated_at` is a freshness stamp only (no comparability/idempotency impact); and ADR-0002 is respected —
the rebuild mints its S3 clients through the same `scout_runtime.guard_real_s3_client()` gate the audit
passed, writing only `edenseek-scout`.

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MINOR | The imports + `ts` computation sat *outside* the per-rebuild try, so a (near-impossible, since `app.py` pre-imports both modules) import/timestamp failure would propagate a 503 despite persisted audits. | **Fixed** — setup is now inside its own guard; `_rebuild_projections` never raises (setup failure → recorded `failed:` for both). |
| 2 | NIT | Registry stamped its own `_now_iso` a few ms after the benchmark's `ts`. | **Fixed** — a single batch `ts` is passed to both rebuilds. |
| 3 | NIT | Only the registry-fails direction was tested. | **Added** `test_benchmark_failure_is_non_fatal_and_independent` (symmetric). |
| 4 | NIT | Discovery runs twice (audit start + registry rebuild); double bucket list. | Accepted — correctness-neutral, consistent with the self-resolve design; a perf follow-up if the issue count grows. |

## 6. Certification statement

Additive; the default path is byte-identical to the certified Increment-1 orchestrator; the rebuild is
best-effort and — after the fold — `_rebuild_projections` cannot raise, so an audit whose reports are
persisted can never become a 503 over a refresh; region resolution is correctly delegated; ADR-0002 is
respected via the shared runtime gate. Adversarial review found no correctness defect; the one MINOR is
fixed and two NITs closed. Suite **487 passed**. **Offline-certified.** With 2e merged, **SXI-2 is complete
and self-refreshing** — a single `--all` audits every issue AND refreshes Health + the per-scope/series
views. Remaining gates: merge → deploy (`git pull` + restart) → run `--all` and verify the `rebuild` block
reports `rebuilt` and the 2c/2d tables populate.
