# Scheduler Activation — Certification Plan (separate operational milestone)

> Certify enabling the **Registry-rebuild scheduler** in production: the opt-in job runs the certified
> `rebuild_discovered` on a cadence, correctly and without harming the certified baseline, and is cleanly
> reversible. **This is a plan only — no activation is performed here.** Activation is an explicit operator
> action executed only after this plan is approved.
>
> - Baseline: `main` `b817270` deployed on the VM; Registry Validation **PASS** (`REGISTRY_VALIDATION_REPORT.md`).
> - Change surface: **environment/config only** — `SCOUT_REGISTRY_REBUILD_ENABLED` (+ interval) + a service
>   restart. **No application code, no IAM, no merge.** The job + flag are already deployed and certified
>   (Increment 6); this milestone flips the flag and certifies runtime behavior.

---

## 1. Objective & success criteria
Confirm, in production, that with the scheduler **enabled**:
1. The Registry-rebuild job **registers** (interval as configured).
2. The **first scheduled run executes** and rebuilds the Registry correctly (logically identical to the
   validated manual rebuild).
3. Runs are **idempotent/stable** across cadence — entries unchanged; only `generated_at` advances; no errors.
4. **No interference** — existing jobs (dataset audit, etc.) and endpoints behave as before; `/registry`
   serves the freshly-rebuilt Registry.
5. **Ownership boundary preserved** — writes only `edenseek-scout/registry/registry.json`; no
   `edenseek-publishing` writes.
6. **Cleanly reversible** — disabling (flag false + restart) returns to the certified disabled state.

**PASS** = all six ✅ with recorded evidence.

## 2. Preconditions
- Registry Validation certified, including the V4-live + V5 operator confirmations.
- Service healthy; scheduler currently **disabled**; `registry/registry.json` present (from validation).
- A chosen cadence. **Recommended:** `SCOUT_REGISTRY_REBUILD_INTERVAL_MINUTES=60` (Registry state changes
  only on Publisher publish/approve; hourly is ample and cheap). For the certification window a shorter
  interval (e.g. 5–15 min) may be used to observe multiple runs quickly, then reset to the operating cadence.

## 3. Procedure (operator on the VM)

### SA0 — Pre-activation snapshot (read-only)
- Record current `registry/registry.json` (`generated_at`, `sha256`, entries) and confirm the flag is off +
  service healthy (`/health` 200).

### SA1 — Enable + restart
```bash
cd ~/Edenseek_Scout
# add to .env (do NOT commit .env):
#   SCOUT_REGISTRY_REBUILD_ENABLED=true
#   SCOUT_REGISTRY_REBUILD_INTERVAL_MINUTES=60      # or a short value for the cert window
sudo systemctl restart edenseek-scout
```

### SA2 — Registration verification
```bash
journalctl -u edenseek-scout --since "2 min ago" | grep -i "registry rebuild"
```
- **Expect:** `Registered Registry rebuild job (every <N> min)` (NOT "disabled"). Existing jobs still logged
  as before.

### SA3 — First scheduled-run verification
- Wait one interval, then:
```bash
journalctl -u edenseek-scout | grep -iE "Scheduled Registry rebuild triggered|Registry rebuild:"
```
- **Expect:** `Scheduled Registry rebuild triggered` → `Registry rebuild: 1 issue(s) discovered, 1 in Registry`.
- Verify `registry/registry.json` updated: new `generated_at`, and **entries logically identical** to SA0 /
  the validated manual rebuild (only `generated_at`/`sha` changed). Authed `GET /registry` reflects it.

### SA4 — Stability / idempotency across cadence
- After **≥2** scheduled runs: confirm each run logs success, entries remain identical (idempotent), no
  tracebacks, the scheduler stays alive, and runs never overlap (`max_instances=1` / `coalesce`).

### SA5 — Non-interference + boundary
- Existing jobs unaffected (dataset audit cadence/logs unchanged); `/health` 200; `/registry` fresh.
- **Boundary:** every rebuild writes only `edenseek-scout/registry/registry.json`; confirm no
  `edenseek-publishing` write attempt in logs (IAM Deny would surface one). Read-only Discovery on publishing.

### SA6 — Reversibility drill (proves clean disable)
- Set `SCOUT_REGISTRY_REBUILD_ENABLED=false`, restart, confirm `Registry rebuild job disabled` and no further
  scheduled triggers. Then re-enable at the chosen operating cadence for the end state (or leave disabled if
  the founder defers — the certification stands either way).

## 4. Evidence to record
`journalctl` lines for registration + ≥2 scheduled runs; the `registry/registry.json` `generated_at`/entries
before and after; `/registry` authed response; confirmation existing jobs are unaffected; the reversibility
toggle logs.

## 5. Deliverable
`SCHEDULER_ACTIVATION_CERTIFICATION_REPORT.md` — per-criterion (SA1–SA6) evidence + PASS/FAIL + verdict, and
the final operating cadence + flag state.

## 6. Rollback / safety
- **Disable is one line + a restart** (`SCOUT_REGISTRY_REBUILD_ENABLED=false`) — immediate, reversible,
  code-unchanged. The `registry/registry.json` projection is rebuildable + S3-versioned.
- The scheduled job only orchestrates the already-certified `rebuild_discovered` (read-only Publisher; single
  Scout write); it introduces no new logic. A failing run is logged and never kills the scheduler.
- No merge, no code change, no IAM change — this milestone is config + runtime certification only.

---

*Plan only — the scheduler is NOT activated by this document. Await founder approval + an explicit operator
activation. Cadence (SA precondition) is a founder decision.*
