# Deployment plan — geometry correctness (Inc 1–3) + runtime safety boundary

> Deploys branch `geometry-correctness-and-runtime-safeguard` (5 commits) to the Oracle VM.
> **Plan only — production is not touched by this document.** Execute only after the branch is
> certified and the founder approves. Deployment is a **separate operational step** from
> development and from any activation.

## What ships
- **Runtime safety boundary** (ADR-0002): `scout_runtime.py` gate on the two real S3 client factories;
  deny-by-default outside production.
- **Geometry correctness (Inc 1–3)**: page-scoped matching + spread-to-spread matching (stratified
  page/spread/total) + quality-weighted `segmentation_accuracy` (`E/(A+FP)`) + resize diagnostics.
  `GEOMETRY_MATCH_VERSION` v1 → **v2** (a comparability boundary).

## ⚠️ Two ordering rules that make this safe

**1. Set `SCOUT_RUNTIME_MODE=production` on the VM BEFORE the new code runs.** The new code
denies-by-default: if the agent starts without this env, it will **refuse to construct its own S3
client** and the scheduler/audit will fail (fail-safe, not fail-open). Setting the env on the *old*
code is a harmless no-op (old code doesn't read it), so set it first.

**2. Deploy is NOT activation.** The scheduler cadence/enable flags are unchanged. Deploying only
makes the corrected code present. The first audit under v2 (scheduled or a manual trigger) will
produce a **new, corrected v2 report** — see §4.

## 1. Preconditions
- Branch certified (hostile review PASS; full suite green; determinism verified).
- Merge `geometry-correctness-and-runtime-safeguard` → `main`, push to GitHub.
- Record the current deployed commit as the rollback point.

## 2. Operator steps (on the VM)

### D0 — set runtime mode FIRST (no-op for the running old code)
```bash
sudo systemctl edit edenseek-scout      # add:  [Service]\nEnvironment=SCOUT_RUNTIME_MODE=production
sudo systemctl daemon-reload
# do NOT restart yet — old code is still running and unaffected
```

### D1 — deploy the code
```bash
cd ~/Edenseek_Scout
git rev-parse HEAD                        # record rollback point
git fetch origin && git pull --ff-only origin main
python -c "import scout_runtime; print(scout_runtime.mode())"   # must print: production
sudo systemctl restart edenseek-scout && sudo systemctl status edenseek-scout --no-pager
```

### D2 — verify service + boundary
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/health          # 200
journalctl -u edenseek-scout --since "2 min ago" | grep -i "ScoutSafetyError"        # expect NONE
```
If `ScoutSafetyError` appears, the env was not set — the agent is denying its own client. Fix D0.

## 3. Success criteria
1. Service restarts clean; `/health` 200.
2. `scout_runtime.mode()` == `production`; **no** `ScoutSafetyError` in logs (the agent can reach S3).
3. Existing read-only endpoints unchanged (`/registry`, `/observability/*`).
4. Scheduler still registered at the same cadence (no activation change).
5. Read-only on `edenseek-publishing`; writes only to `edenseek-scout`.

## 4. Expected first-audit behavior (v1 → v2)
The ledger marks `rev_0be8dc34` processed under the **v1** fingerprint. v2 has a **different**
methodology fingerprint, so the next audit sees the revision as not-yet-processed under v2 and
produces a **fresh v2 report** (`run000004`) with the corrected, stratified numbers + segmentation
accuracy. This is expected and correct — it is the corrected metrics going live, a clean new
`run_id`, not a mutation of the archived v1 report. The dashboard will then show the v2 numbers.
Decide separately whether to trigger this manually or let the scheduler do it (activation is not
part of this deploy).

## 5. Rollback
- `git checkout <rollback-commit>` + `sudo systemctl restart edenseek-scout` (code-only, immediate).
- Optionally remove the `SCOUT_RUNTIME_MODE` override (old code ignores it either way).
- Any v2 report already persisted stays in the immutable archive (a comparability-versioned entry);
  it is not a corruption of v1.

---
*Plan only. Await certification + founder approval before executing.*
