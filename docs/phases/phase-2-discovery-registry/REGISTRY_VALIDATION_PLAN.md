# Registry Validation — Execution Plan

> Milestone: **Registry validation only.** Validate the deployed Phase-2 Registry lifecycle in production —
> a manual rebuild against live Publisher data produces a **correct, complete, idempotent** Registry that
> the `/registry` endpoint serves faithfully. **The Registry-rebuild scheduler stays DISABLED throughout;**
> activation is a separate operational certification handled *after* this passes.
>
> Baseline: `main` `b817270` (code `69bcae5`) deployed on the Oracle VM. Prepared 2026-07-29 — **plan only;
> nothing executed yet.**

---

## 1. Objective & success criteria

Confirm, on the deployed production service, that:
1. **Rebuild works** against live Publisher data (governed, manual).
2. **Contents are correct** — every entry's revision/state/audit is derived from authoritative objects.
3. **Contents are complete** — the entry set equals the discovered issue set; no missing/extra entries.
4. **Idempotent** — a second rebuild changes nothing meaningful (only the build timestamp differs).
5. **`/registry` is faithful** — the endpoint serves exactly the persisted, rebuilt Registry.
6. **Scheduler stays off** — no scheduled rebuild runs during the exercise.

**Milestone PASS** = all six ✅ with recorded evidence.

## 2. Preconditions & constraints
- Phase 2 deployed on the VM; `SCOUT_REGISTRY_REBUILD_ENABLED` unset/false (verify at start, keep unchanged).
- Read-only on `edenseek-publishing`; the only write is `edenseek-scout/registry/registry.json`
  (latest-state, versioned/recoverable). No Publisher coordination needed.
- **Do NOT enable the scheduler.** Do NOT change application code or IAM.

## 3. Roles
- **Operator (VM):** runs the governed rebuilds (deployed code) + the authed endpoint checks; captures CLI
  stdout + endpoint responses.
- **Engineering session:** independent read-only verification of `edenseek-scout` + the Publisher source
  objects; idempotency diff; authors the Registry Validation Report.

## 4. Procedure

### V0 — Baseline (read-only)
- Confirm the scheduler flag: on the VM `grep -i SCOUT_REGISTRY_REBUILD_ENABLED .env` → expect unset/false;
  `journalctl -u edenseek-scout | grep -i "registry rebuild job"` → **"disabled"**.
- Engineering session records the current `registry/registry.json` (sha256, `generated_at`, entries) as the
  pre-validation baseline (it exists from the earlier governed run).

### V1 — Manual rebuild #1 (governed, deployed code)
- Operator on the VM:
  ```bash
  cd ~/Edenseek_Scout
  [ -d venv ] && source venv/bin/activate || source .venv/bin/activate
  python scout_registry.py --discover | tee /tmp/registry_rebuild_1.json
  ```
- Capture the CLI summary: `discovered`, `count`, `sha256`, `generated_at`, and full `entries`.
- Expected: `discovered ≥ 1`; `count == discovered`; readback-verified log line
  ("Registry persisted + verified").

### V2 — Correctness & completeness verification (read-only)
Engineering session cross-checks the rebuilt entry(ies) against **authoritative sources**:
- **Discovery set** = the issues with `approved/published.json` under `publishers/` (expected today: the
  tree-of-one `issue_001`). No missing/extra issues; identity chain
  (`publisher/title_group/series/issue`) correct.
- **Revision** = the current `approved/published.json` pointer (`rev_0be8dc34…`).
- **State** = the verbatim `canonical_dataset_state` from `reviews/{review_id}/platform_approval.json`
  (`edenseek_approved`).
- **Audit linkage** = Scout's own index/ledger for the current revision (`audited`, `run_seq 3`,
  `run_id run_833dfc915be60481`, `report_id …run000003`).
- **Cross-consistency:** entry matches the certified Phase-1 baseline.
- **Completeness:** `count` == number of discovered issues; every entry has a full identity + `publication`
  + `audit` block.

### V3 — Idempotency (rebuild #2)
- Operator: run the governed rebuild a **second** time:
  ```bash
  python scout_registry.py --discover | tee /tmp/registry_rebuild_2.json
  ```
- **Idempotency criterion (explicit):** the derived projection is stable — rebuild #2's `entries` (and
  `count`, `registry_version`, identity/state/audit) are **byte-identical** to rebuild #1's. The **only**
  permitted difference is `generated_at` (a wall-clock build timestamp), which also changes the object
  `sha256`. Any difference in `entries`/`count`/state/audit is a **FAIL**.
- **Verification:** diff `/tmp/registry_rebuild_1.json` vs `_2.json` with `generated_at` normalized out →
  must be empty. (Engineering session performs the normalized diff.)

### V4 — `/registry` endpoint validation
- Operator (authed) against the live service:
  ```bash
  curl -s -u "$USER:$PASS" https://scout.edenseek.com/registry      > /tmp/registry_endpoint.json
  curl -s -u "$USER:$PASS" https://scout.edenseek.com/registry/tree > /tmp/registry_tree.json
  curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/registry   # expect 401 (no auth)
  ```
- **Pass criteria:**
  - `/registry` (authed) → 200 and its body **equals the persisted `registry/registry.json`** after rebuild
    #2 (same `count` + `entries`).
  - `/registry/tree` → 200 and equals `tree_view` of that Registry (publisher → … → issue).
  - Unauthenticated → 401.

### V5 — Scheduler-disabled confirmation
- Re-confirm `journalctl` shows the Registry-rebuild job **disabled** and that the **only** rebuilds during
  the window were the two manual ones (no scheduled trigger fired). `SCOUT_REGISTRY_REBUILD_ENABLED`
  unchanged (false).

## 5. Evidence to record
CLI outputs (`registry_rebuild_1/2.json`), the normalized idempotency diff, the endpoint responses
(`/registry`, `/registry/tree`, the 401), the read-only cross-verification of source objects, and the
`journalctl` scheduler-disabled lines.

## 6. Deliverable — Registry Validation Report
A report (`docs/phases/phase-2-discovery-registry/REGISTRY_VALIDATION_REPORT.md`) recording, per criterion
(V0–V5), the evidence and a PASS/FAIL, with an overall verdict. On PASS, it certifies the Registry lifecycle
in production and clears the *separate* scheduler-activation certification. On FAIL, it records the defect;
no scheduler activation proceeds.

## 7. Safety / rollback
- Read-only on the Publisher; the only mutation is the latest-state `registry/registry.json` (S3-versioned,
  recoverable; a prior version is one restore away). No code, config, or IAM change. The scheduler is never
  enabled. Aborting at any step leaves production exactly as deployed.

---

*Plan only — awaiting founder go-ahead to execute. Execution split: operator runs the VM rebuilds +
endpoint checks; the engineering session performs read-only verification and authors the report.*
