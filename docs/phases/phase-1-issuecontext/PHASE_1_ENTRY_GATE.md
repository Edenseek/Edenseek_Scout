# Phase 1 — IssueContext Plumbing · Entry Gate

**Status:** OPEN (blocking). Phase 1 **application-code implementation must not begin** until **every**
criterion below is satisfied and recorded. This gate operationalizes ADR-0001 §Sequencing (binding):
implementation starts only after the Publisher 6.4 demonstration + close-out.

## Required evidence (all must be TRUE and recorded)

| # | Criterion | Evidence to record | State |
|---|---|---|---|
| 1 | **Publisher 6.4 demonstration completed** | Publisher bridge confirmation of the 6.4 end-to-end demo (published revision id) | ✅ `rev_0be8dc34` certified (trigger doc 2026-07-29) |
| 2 | **Publisher 6.4 close-out completed** | Publisher bridge confirmation of the 6.x close-out | ✅ `2026-07-29_publisher_6_4_closeout_PHASE1_TRIGGER.md` |
| 3 | **Publisher repository clean and pushed** | Publisher-side statement (via bridge) that its repo is clean + pushed (owned by the Edenseek session, not Scout) | ✅ trigger doc (branch `week10-canonical-issue-workspace-poc`, clean) |
| 4 | **Bridge acknowledgement available** | A Publisher bridge doc acknowledging Scout's ADR ratification / clearing Phase 1 to start | ✅ trigger doc "You are clear to begin Phase 1" |
| 5 | **Scout ADR ratified and committed** | `docs/architecture/ADR-0001-scout-publisher-observability-architecture.md` committed on `main` (the freeze point) | ✅ done (Phase 0, `da76d05`) |
| 6 | **Scout production baseline still healthy** | Live checks green: `/health` 200; dashboard loads; `/audit-review/archive`, `/benchmark/platform`, `/intelligence/*`, `/schemas` return valid; a canonical audit reconciles idempotently; **no `edenseek-publishing` writes** | ✅ data layer green (see Gate result); ⚠ authed HTTP sweep operator-confirmed (prod auth not in this session) |
| 7 | **Current Scout branch + rollback point recorded** | `main` HEAD commit hash captured as the certified baseline / rollback target | ✅ `main` @ `032daca` |

## Gate result — recorded 2026-07-29 (read-only)

**Rollback point (criterion 7):** `main` @ `032dacae82d7d5ed552a30ba0da912fd1a6955d9` (local == origin, clean).

**Production baseline (criterion 6):**
- `GET https://scout.edenseek.com/health` → **200** (service live).
- Authed endpoint sweep (`/dashboard`, `/audit-review/archive`, `/benchmark/platform`, `/intelligence/*`,
  `/schemas`, `/reports/latest`) returned **401 from this session** — the local `.env` auth does not match
  the VM's production auth env (expected; env vars are a deploy-time VM exception). These are
  **operator-confirmable** on the VM/browser and have been exercised live this session.
- **Data-layer baseline (authoritative, read from `edenseek-scout`):**
  - `report_index` v1 — **3 entries**: `run000003`/`run000002`/`run000001`.
  - latest `scout_delta_report` = `…rev_0be8dc34…::run000003`, `run_id run_833dfc915be60481`, `run_seq 3`,
    `delta_report_sha256 fe66c142…`, `metadata_status computed`, **`comparable_fields 337`**.
  - latest `scout_report` = `…rev_0be8dc34…::run000004`, `run_seq 4`.
  - `ledger` v1 — **2 processed revisions**: `rev_0be8dc34` (`run3`, manual) + `rev_a8c65a83` (`run2`,
    certification), fingerprint `fp_580cbeb1f41b`.
- **Ownership boundary:** every gate operation was a read; the only writer remains `edenseek-scout`
  (IAM-enforced Deny on `edenseek-publishing`); no publishing writes.

This fingerprint is the pre-flight baseline for the Phase-1 byte-equivalence re-cert (runbook §Certification 3):
after the refactor, `context=from_env()` must reconcile to `run000003`/`run000004` with **no new `run_seq`**
and identical `run_id`/`report_id`/`sha`.

**Gate status:** criteria 1–5 + 7 satisfied; criterion 6 data-layer green (authed HTTP sweep deferred to
operator). Clear to open `phase-1-issuecontext` **on founder go-ahead**.

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
