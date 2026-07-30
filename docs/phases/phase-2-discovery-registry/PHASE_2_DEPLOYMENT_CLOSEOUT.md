# Phase 2 — Production Deployment Close-Out

> Close-out + planning record for the Phase 2 (Discovery → Registry → Scheduler) production deployment.
> **Planning only — no new functionality.** Companion to `PHASE_1_ARCHITECTURE_AND_CERTIFICATION.md` and the
> per-increment hostile reviews in this directory.
>
> - **`main`:** `b817270` (code merge `69bcae5`; Phase 1 + Phase 2). **Rollback point:** `3c608fc`.
> - **Deployed to:** Oracle VM (production). **Date:** 2026-07-29.
> - **Scheduler execution:** intentionally **DISABLED** (`SCOUT_REGISTRY_REBUILD_ENABLED` unset/false).

---

## 1. Deployment summary

| Item | Detail |
|------|--------|
| Deployed code | `main` (Phase 1 IssueContext — behavior-neutral — **+** Phase 2 Discovery/Registry/Scheduler) |
| Method | Standard discipline: local → GitHub → VM `git pull` + `sudo systemctl restart edenseek-scout` |
| First deployment of Phase 1 | Yes — Phase 1 had never been deployed; it is behavior-neutral (`context=None` everywhere), so existing behavior is byte-for-byte |
| New dependencies | None (no `requirements` change) |
| IAM / config changes | None — `.env` and IAM unchanged; ownership Deny on `edenseek-publishing` writes holds |
| Scheduler policy | Registry-rebuild job **off by default**; deployment did **not** enable it (deployment ≠ activation) |
| Rollback | `git checkout 3c608fc` + restart — code-only, immediate |

**What changed operationally:** two additive read-only endpoints (`GET /registry`, `/registry/tree`) and the
new `scout_registry` / `scout_discovery` modules are now present in production; the opt-in scheduled rebuild
job is registered-but-disabled. No existing endpoint, job, or audit behavior changed.

---

## 2. Operational certification report

Certified during deployment validation (operator-run on the VM, plus independent read-only verification of
`edenseek-scout` from the engineering session):

| Check | Result | Evidence |
|-------|--------|----------|
| Service restarted cleanly | ✅ | `systemctl` healthy; `/health` 200 |
| Scheduler initialized correctly | ✅ | jobs registered; **Registry rebuild job disabled** (`SCOUT_REGISTRY_REBUILD_ENABLED=false`) as intended |
| Registry rebuild remains disabled | ✅ | opt-in flag unset; no rebuild job runs |
| Manual production audit executed | ✅ | dataset audit run on the VM |
| Reports published to the Scout Output Layer | ✅ | consolidated Scout Report **`run000006`** in `edenseek-scout` (run_seq 6, `publisher_revision_id rev_0be8dc34…`, quality_score 72) — independently re-read |
| Read-back verification passed | ✅ | R1 write helpers readback SHA-256 verified |
| End-to-end Publisher → Scout → Publisher | ✅ | Publisher **discovered, read, and interpreted `run000006`**, closing the loop |
| Registry read path live | ✅ | `registry/registry.json` (v1, count 1) serves the tree-of-one: `issue_001` / `edenseek_approved` / `audited` / `run_seq 3` |
| Ownership boundary preserved | ✅ | all writes to `edenseek-scout` only; `edenseek-publishing` read-only (scheduler off ⇒ no rebuild writes) |
| Existing behavior unchanged | ✅ | Phase 1 behavior-neutral; Phase 2 additive only |

**Verdict:** Phase 2 is **deployed and operationally certified in production** with scheduler execution
disabled. The Publisher→Scout→Publisher pipeline is confirmed end-to-end on the live service.

**Lifecycle position:** Implemented → Certified → Merged → **Deployed** → **Verified** → *Enabled (held)*.

---

## 3. Recommended follow-up tasks

Ordered by priority; none block the current certified baseline.

1. **Registry validation window (short, low-effort).** Observe `GET /registry` in production; run one
   governed `python scout_registry.py --discover` on the VM to confirm the exact code path the scheduler
   would call succeeds in the production environment before it runs unattended.
2. **Scheduler activation (gated, minimal).** After (1): set `SCOUT_REGISTRY_REBUILD_ENABLED=true`
   (+ optional `SCOUT_REGISTRY_REBUILD_INTERVAL_MINUTES`, default 60) and restart. Explicit operational
   decision — never combined with a deploy.
3. **Documentation refresh (drift discipline).** Update `scout_v0.3_synopsis.md`,
   `scout_status_and_tech_debt.md`, `scout_beta_roadmap.md` to reflect Phase 1 + Phase 2 shipped
   (IssueContext, Registry, Discovery, scheduler) and the current production baseline.
4. **Cross-process safety (existing tech debt).** The scheduler is in-process / single-worker; enabling the
   rebuild alongside the audit jobs keeps that assumption. The SQLite migration (Priority 4) remains the
   durable fix; track it before scaling workers.
5. **Registry entry enrichment (small).** `resolved_at` is currently `null` (the pure resolver takes it as
   input); stamp resolution time in the governed/scheduled rebuild for better observability.
6. **Discovery breadth (optional).** Discovery enumerates *published* issues (`approved/published.json`
   marker). If unpublished issues should appear in the Registry, broaden enumeration (resolver already
   tolerates unpublished).
7. **Deferred, governed items (no action unless a milestone needs them):** Phase-1 `from_env()` activation
   in the audit flow (then retire the `context=None` env branches) as its own certified increment; a Registry
   dashboard tab (review UI together per the standing note); the three optional Publisher Gate-C enhancements.

---

## 4. Next engineering milestone — recommendation

Three candidates were on the table (Registry validation, scheduler activation, other). Recommendation:

**Near-term (operational, this week):** complete the lifecycle — **Registry validation → scheduler
activation** (tasks 1–2 above). Small, gated, high-value: it makes the Registry continuously fresh with
essentially no new code, and it's the natural final step of the deployment lifecycle.

**Next engineering milestone (primary recommendation): Registry-backed Publisher Observability (ADR-0001
D8).** With Discovery + the Registry live, the platform's stated purpose is now buildable additively:
publisher / series / issue rollup views, cross-series benchmarking, and trend/regression detection as new
read-only projections + views over the Registry and the existing index/benchmark/intelligence artifacts.
This continues the certified, additive, hostile-reviewed increment pattern, stays advisory (Charter §4), and
delivers user-facing value on the certified foundation. It also exercises the D6 rollup model with real
multi-signal data before multi-issue scale arrives.

**Alternative milestone (secondary): audit-path convergence.** Unify the two audit entry points
(dataset-quality + synchronization/delta) into one revision-oriented **analyzer-registry Audit** where
applicability is a pure function of canonical facts (Principle P1). This is a larger internal refactor that
sets up future analyzers; higher risk/effort than D8 and better sequenced after the observability views prove
the Registry in production.

**Recommendation:** validate + activate the scheduler operationally now, then take **D8 Registry-backed
Observability** as the next engineering milestone; hold the audit-path convergence as a later, deliberately
scoped architectural effort.

---

*Prepared as a close-out and planning artifact. No functionality was implemented. Await founder direction
before beginning any milestone; scheduler enablement remains an explicit operational decision.*
