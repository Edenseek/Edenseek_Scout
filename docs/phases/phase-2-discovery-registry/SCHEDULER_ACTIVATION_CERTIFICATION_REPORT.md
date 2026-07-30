# Scheduler Activation — Certification Report

> Execution of `SCHEDULER_ACTIVATION_PLAN.md` at the founder-approved **60-minute cadence**.
> **Result: PASS — the Registry-rebuild scheduler is activated and certified in production.**
>
> - Date: 2026-07-30. Baseline: `main` (Phase 2 code `69bcae5`) deployed on the Oracle VM.
> - End state: `SCOUT_REGISTRY_REBUILD_ENABLED=true`, `SCOUT_REGISTRY_REBUILD_INTERVAL_MINUTES=60`.
> - Change surface: **config/runtime only** (flag + interval + restart). No app code, IAM, or merge.
> - Evidence: operator `journalctl` (VM) + engineering-session read-only S3 corroboration of
>   `edenseek-scout/registry/registry.json` at each stage.

---

## Result: PASS

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| SA1 | Enable + restart | ✅ | `.env` set `ENABLED=true` / `INTERVAL=60`; service restarted 16:31:24 |
| SA2 | Job registers | ✅ | `16:31:24 Registered Registry rebuild job (every 60 min)`; no premature run (S3 unchanged post-restart) |
| SA3 | First scheduled run executes + rebuilds correctly | ✅ | `17:31:24 Scheduled Registry rebuild triggered` → `17:31:27 Registry rebuild: 1 issue(s) discovered, 1 in Registry`; S3 `generated_at` advanced to `17:31:24.806Z` (matches the log trigger) |
| SA4 | Idempotent / stable across ≥2 runs | ✅ | run 2 at `18:31:24` (+60 min, exact); entries_fingerprint **`2f6f9dbd…` unchanged** across baseline / run 1 / run 2 — only `generated_at`/SHA advance; single trigger per run (no overlap; `max_instances=1`) |
| SA5 | No interference; ownership boundary | ✅ | no errors/exceptions/failed jobs in logs; existing jobs unaffected; every rebuild wrote **only** `edenseek-scout/registry/registry.json` (read-only Discovery; IAM Deny on `edenseek-publishing`) |
| SA6 | Cleanly reversible | ✅ (documented) | disable = `SCOUT_REGISTRY_REBUILD_ENABLED=false` + restart — the certified *disabled* state immediately preceded activation, so clean disable is proven; a live off/on drill was **not** exercised, to avoid interrupting the now-certified live scheduler |

## Timeline & corroboration

| Stage | Log (server = UTC) | S3 `registry/registry.json` `generated_at` | entries_fingerprint | object SHA (24) |
|-------|--------------------|--------------------------------------------|---------------------|-----------------|
| SA0 baseline | — (validation rebuild) | `2026-07-30T03:02:39.760Z` | `2f6f9dbd…` | `d1118445…` |
| SA2 registration | `16:31:24` registered | (unchanged — no premature run) | `2f6f9dbd…` | `d1118445…` |
| Run 1 | `17:31:24`→`17:31:27` | `2026-07-30T17:31:24.806Z` | `2f6f9dbd…` | `fd01b3a2…` |
| Run 2 | `18:31:24`→`18:31:27` | `2026-07-30T18:31:24.804Z` | `2f6f9dbd…` | `81950d44…` |

- **Cadence deterministic:** registration → run 1 → run 2 at exactly 60-min spacing.
- **Temporal linkage:** each run's S3 `generated_at` equals its `journalctl` trigger time — the persisted
  object is provably the product of that scheduled run.
- **Idempotency / no drift:** the logical fingerprint (`entries`, `generated_at` excluded — the
  founder-approved convention) is **constant** across all three states; only the build timestamp and object
  SHA change.
- **Registry entry (invariant across all runs):** `issue_001` / `edenseek_approved` / `audited` /
  `run_seq 3` / `run_833dfc915be60481` / `run000003`.

## Verdict
The Registry-rebuild scheduler is **activated and certified in production at a 60-minute cadence**. Two
consecutive autonomous executions completed cleanly, deterministically on cadence, writing only the derived
Registry artifact, with byte-stable logical contents (idempotent, no drift) and no errors, duplicate work,
or unexpected log messages. **End state: enabled (60 min).** No other production configuration was changed.

**Reversibility:** disabling is a one-line flag (`SCOUT_REGISTRY_REBUILD_ENABLED=false`) + restart — immediate
and code-unchanged; the Registry projection remains rebuildable + S3-versioned.

*Phase 2 (Discovery → Registry → Scheduler) is now fully deployed, certified, and operational, with autonomous
Registry maintenance running on the certified pipeline.*
