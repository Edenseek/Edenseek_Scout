# D8 Increment 1 — Deployment & Operator Validation Plan (separate operational increment)

> Deploy the code-complete D8 Increment 1 (`/observability/health`) to production and validate it, keeping
> deployment and implementation boundaries clean. **Plan only — no deployment is performed here.** Execute
> only after founder review of this plan.
>
> - Deploy target: `main` `f7952b8` (D8 Inc 1 merged). Currently deployed on the VM: Phase-2 code `69bcae5`.
> - **Change since the running deployment = D8 Increment 1 only** (everything between `69bcae5` and
>   `f7952b8` is docs, except the additive `scout_observability.py` + one `app.py` route). Behavior-neutral
>   for all existing endpoints; adds `GET /observability/health`.

## 1. Objective & success criteria
Confirm, in production, that after deploying D8 Increment 1:
1. Service restarts cleanly; `/health` 200.
2. **Existing behavior unchanged** — existing endpoints + the (enabled) scheduler jobs behave as before.
3. **New endpoint live** — authed `GET /observability/health` returns the correct Issue Health projection.
4. **Boundary intact** — read-only; no `edenseek-publishing` writes.
5. **Cleanly reversible.**

**PASS** = all five ✅ with recorded evidence.

## 2. Preconditions
- D8 Increment 1 certified code-complete (this milestone), merged to `main`.
- No new environment/config is required by D8 (no new env vars). **Do not change any other config.**
- Note the current scheduler state: `SCOUT_REGISTRY_REBUILD_ENABLED=true` (60 min) — it must survive the
  restart and keep running (unaffected by D8).

## 3. Procedure (operator, on the VM)

### D0 — Pre-deploy snapshot
- Record the deployed commit (`git rev-parse HEAD`) as the rollback point; `/health` 200; note the last
  scheduled Registry rebuild in the logs.

### D1 — Deploy
```bash
cd ~/Edenseek_Scout
git fetch origin && git checkout main && git pull          # -> f7952b8
git log --oneline -1                                        # expect f7952b8
# No .env / config change. No new dependencies.
sudo systemctl restart edenseek-scout
sudo systemctl status edenseek-scout --no-pager
```

### D2 — Health + non-interference
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/health          # 200
journalctl -u edenseek-scout --since "2 min ago" | grep -i "registry rebuild"        # job still Registered (every 60 min)
```
- Spot-check an existing endpoint (e.g. `/registry` authed) behaves as before.

### D3 — New endpoint validation
```bash
U=$(grep -E '^SCOUT_USERNAME=' .env | cut -d= -f2- | tr -d '\r"'"'"')
P=$(grep -E '^SCOUT_PASSWORD=' .env | cut -d= -f2- | tr -d '\r"'"'"')
curl -s -u "$U:$P" https://scout.edenseek.com/observability/health | python3 -m json.tool
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/observability/health   # no-auth -> 401
```
- **Expect:** `projection: "issue_health"`, `summary {"healthy":1,"attention":0,"unknown":0,"total":1}`,
  `issue_001` → `health: "healthy"` (matches the certified Registry: `edenseek_approved` + `audited`);
  no-auth → 401.

### D4 — Boundary + scheduler continuity
- Confirm the next scheduled Registry rebuild fires normally post-deploy (`Scheduled Registry rebuild
  triggered` at the next hour boundary) and writes only `edenseek-scout` — D8 changed nothing there.

## 4. Evidence to record
`/health` code; the `registry rebuild` registration line post-restart; the authed `/observability/health`
body + no-auth 401; confirmation an existing endpoint is unchanged; the next scheduled-rebuild log line.

## 5. Deliverable
`INCREMENT_1_DEPLOYMENT_CERTIFICATION_REPORT.md` — per-criterion (D1–D4) evidence + PASS/FAIL + verdict.

## 6. Rollback / safety
- Rollback = `git checkout <pre-deploy commit>` + restart — **code-only**, immediate; `.env`/IAM unchanged.
- D8 is additive + read-only (advisory); it introduces no new writes and no Publisher access. The scheduler,
  Registry, and audit path are untouched by this deploy.

---

*Plan only — production is not touched by this document. Await founder review of the plan before deploying.*
