# D8 Increment 3 — Deployment & Operator Validation Plan (separate operational increment)

> Deploy the code-complete D8 Increment 3 (Cross-Series Health) to production and validate it. **Plan only —
> no deployment here.** Execute only after founder review.
>
> - Deploy target: `main` `75b2b1f` (D8 Inc 3 merged). Currently deployed: `fa95ba4` (D8 Inc 2).
> - **Change since the running deployment = D8 Increment 3 only** — additive (`cross_series_health` + one
>   route + docs incl. Principle P2). Behavior-neutral for all existing endpoints; adds
>   `/observability/health/cross-series`.

## 1. Objective & success criteria
After deploying D8 Increment 3, confirm:
1. Service restarts cleanly; `/health` 200.
2. **Existing behavior unchanged** — `/observability/health` (Issue), `/series`, `/publisher`, `/registry`,
   and the scheduler all behave as before.
3. **New endpoint live + correct** — authed `/observability/health/cross-series` → `summary {healthy:1,…}`,
   `attention []`, `by_health.healthy = [society_of_killers]`; no-auth → 401 (was 404).
4. **Recompute-from-below holds** — Cross-Series is consistent with Series Health over the live Registry
   (`cross.summary == series.summary`; attention == the non-healthy series).
5. **Boundary intact** — read-only; Registry fingerprint unchanged; no `edenseek-publishing` writes.
6. **Cleanly reversible.**

**PASS** = all six ✅ with recorded evidence.

## 2. Preconditions
- D8 Increment 3 certified code-complete, merged to `main`.
- No new environment/config required. **Do not change other config.** Scheduler
  (`SCOUT_REGISTRY_REBUILD_ENABLED=true`, 60 min) must survive the restart, unaffected.

## 3. Procedure (operator, on the VM)

### D0 — Pre-deploy snapshot
- Record deployed commit (`git rev-parse HEAD`) as the rollback point; `/health` 200;
  `/observability/health/cross-series` currently **404** (→ 401 after deploy).

### D1 — Deploy
```bash
cd ~/Edenseek_Scout
git fetch origin && git pull --ff-only origin main        # -> 75b2b1f
git log --oneline -1                                       # expect 75b2b1f
grep -c '@app.get("/observability/health/cross-series")' app.py   # expect 1
sudo systemctl restart edenseek-scout && sudo systemctl status edenseek-scout --no-pager
```

### D2 — Existing surface unchanged
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/health                 # 200
U=$(grep -E '^SCOUT_USERNAME=' .env | cut -d= -f2- | tr -d '\r"'"'"'); P=$(grep -E '^SCOUT_PASSWORD=' .env | cut -d= -f2- | tr -d '\r"'"'"')
curl -s -u "$U:$P" https://scout.edenseek.com/observability/health/series | python3 -m json.tool   # unchanged
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/registry                 # 401 (unchanged)
journalctl -u edenseek-scout --since "2 min ago" | grep -i "registry rebuild"                 # Registered (every 60 min)
```

### D3 — New endpoint
```bash
curl -s -u "$U:$P" https://scout.edenseek.com/observability/health/cross-series | python3 -m json.tool
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/observability/health/cross-series   # 401 no-auth
```
- **Expect:** `projection: "cross_series_health"`, `summary {healthy:1, attention:0, unknown:0, total:1}`,
  `attention []`, `by_health.healthy = ["publishers/…/series/society_of_killers"]`.

### D4 — Recompute-from-below + boundary + scheduler
- Engineering session independently recomputes `cross_series_health` from the live Registry and confirms it
  matches the endpoint + `cross.summary == series.summary`; Registry fingerprint unchanged; next scheduled
  rebuild fires; writes only `edenseek-scout`.

## 4. Evidence to record
`/health`; unchanged `/series` + `/registry` 401; the new authed body + its 401; the `registry rebuild`
line; the coherence recomputation.

## 5. Deliverable
`INCREMENT_3_DEPLOYMENT_CERTIFICATION_REPORT.md` — per-criterion (D1–D4) evidence + PASS/FAIL + verdict.

## 6. Rollback / safety
- Rollback = `git checkout fa95ba4` + restart — code-only, immediate; `.env`/IAM unchanged.
- Increment 3 is additive + read-only (advisory); no new write, no Publisher access; scheduler/Registry/audit
  path untouched.

---

*Plan only — production is not touched by this document. Await founder review before deploying.*
