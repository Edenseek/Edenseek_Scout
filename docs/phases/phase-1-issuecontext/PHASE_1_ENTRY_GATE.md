# Phase 1 — IssueContext Plumbing · Entry Gate

**Status:** OPEN (blocking). Phase 1 **application-code implementation must not begin** until **every**
criterion below is satisfied and recorded. This gate operationalizes ADR-0001 §Sequencing (binding):
implementation starts only after the Publisher 6.4 demonstration + close-out.

## Required evidence (all must be TRUE and recorded)

| # | Criterion | Evidence to record | State |
|---|---|---|---|
| 1 | **Publisher 6.4 demonstration completed** | Publisher bridge confirmation of the 6.4 end-to-end demo (published revision id) | ☐ pending |
| 2 | **Publisher 6.4 close-out completed** | Publisher bridge confirmation of the 6.x close-out | ☐ pending |
| 3 | **Publisher repository clean and pushed** | Publisher-side statement (via bridge) that its repo is clean + pushed (owned by the Edenseek session, not Scout) | ☐ pending |
| 4 | **Bridge acknowledgement available** | A Publisher bridge doc acknowledging Scout's ADR ratification / clearing Phase 1 to start | ☐ pending |
| 5 | **Scout ADR ratified and committed** | `docs/architecture/ADR-0001-scout-publisher-observability-architecture.md` committed on `main` (the freeze point) | ✅ done (Phase 0) |
| 6 | **Scout production baseline still healthy** | Live checks green: `/health` 200; dashboard loads; `/audit-review/archive`, `/benchmark/platform`, `/intelligence/*`, `/schemas` return valid; a canonical audit reconciles idempotently; **no `edenseek-publishing` writes** | ☐ verify at gate time |
| 7 | **Current Scout branch + rollback point recorded** | `main` HEAD commit hash captured as the certified baseline / rollback target | ☐ record at gate time |

## Gate procedure
1. Collect evidence for 1–4 from the Publisher via the `publisher_bridge` (do **not** infer completion;
   require an explicit Publisher signal).
2. Confirm 5 (already satisfied in Phase 0) and record the ADR commit hash.
3. Run the production baseline health checks (6) read-only against the live VM/service; record results.
4. Record the `main` HEAD hash as the rollback point (7).
5. Only when 1–7 are all satisfied: open the `phase-1-issuecontext` branch and begin the runbook.

## Explicitly NOT part of the gate / Phase 1
- No Discovery, Registry, scheduler, or dashboard work (later phases).
- No production configuration change; no redeploy as part of starting Phase 1.
- No Publisher-side change is required to pass this gate (the gate waits on the Publisher's own 6.4
  milestone, not on any Publisher work for Scout).

## Founder authority
The founder's 6.4 close-out signal (relayed via the bridge) is the authoritative trigger. Absent that
signal, Phase 1 remains not-started regardless of Scout readiness.
