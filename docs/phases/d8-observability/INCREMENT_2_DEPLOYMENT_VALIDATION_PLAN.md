# D8 Increment 2 — Deployment & Operator Validation Plan (separate operational increment)

> Deploy the code-complete D8 Increment 2 (Series & Publisher Health rollups) to production and validate it,
> keeping deployment separate from development. **Plan only — no deployment performed here.** Execute only
> after founder review.
>
> - Deploy target: `main` `615278e` (D8 Inc 2 merged). Currently deployed: `4857ed2` (D8 Inc 1).
> - **Change since the running deployment = D8 Increment 2 only** — additive (`series_health` /
>   `publisher_health` + two routes); everything else docs. Behavior-neutral for all existing endpoints
>   (incl. the certified `/observability/health`); adds `/observability/health/series` + `/publisher`.

## 1. Objective & success criteria
Confirm, in production, that after deploying D8 Increment 2:
1. Service restarts cleanly; `/health` 200.
2. **Existing behavior unchanged** — `/observability/health` (Issue Health), `/registry`, `/registry/tree`,
   and the (enabled) scheduler all behave as before.
3. **New endpoints live + correct** — authed `/observability/health/series` → `society_of_killers = healthy`;
   `/observability/health/publisher` → `edenseek = healthy`; no-auth → 401.
4. **Hierarchy coherent** — Series/Publisher rollups are consistent with Issue Health over the live Registry
   (independently recomputable; `publisher == roll_up(all issues)`).
5. **Boundary intact** — read-only; no `edenseek-publishing` writes.
6. **Cleanly reversible.**

**PASS** = all six ✅ with recorded evidence.

## 2. Preconditions
- D8 Increment 2 certified code-complete (this milestone), merged to `main`.
- No new environment/config required (no new env vars). **Do not change any other config.**
- Scheduler currently `SCOUT_REGISTRY_REBUILD_ENABLED=true` (60 min) — must survive the restart, unaffected.

## 3. Procedure (operator, on the VM)

### D0 — Pre-deploy snapshot
- Record deployed commit (`git rev-parse HEAD`) as the rollback point; `/health` 200; note that
  `/observability/health/series` currently returns **404** (route absent → will become 401 after deploy).

### D1 — Deploy
```bash
cd ~/Edenseek_Scout
git fetch origin && git checkout main && git pull          # -> 615278e
git log --oneline -1                                        # expect 615278e
# No .env/config change; no new dependencies.
sudo systemctl restart edenseek-scout && sudo systemctl status edenseek-scout --no-pager
```

### D2 — Health + non-interference (existing surface unchanged)
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/health                 # 200
U=$(grep -E '^SCOUT_USERNAME=' .env | cut -d= -f2- | tr -d '\r"'"'"'); P=$(grep -E '^SCOUT_PASSWORD=' .env | cut -d= -f2- | tr -d '\r"'"'"')
curl -s -u "$U:$P" https://scout.edenseek.com/observability/health | python3 -m json.tool  # unchanged (issue_health, healthy 1/1)
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/registry                # 401 (unchanged)
journalctl -u edenseek-scout --since "2 min ago" | grep -i "registry rebuild"               # Registered (every 60 min)
```

### D3 — New rollup endpoints
```bash
curl -s -u "$U:$P" https://scout.edenseek.com/observability/health/series    | python3 -m json.tool
curl -s -u "$U:$P" https://scout.edenseek.com/observability/health/publisher | python3 -m json.tool
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/observability/health/series      # 401 no-auth
curl -s -o /dev/null -w "%{http_code}\n" https://scout.edenseek.com/observability/health/publisher   # 401 no-auth
```
- **Expect series:** `projection: "series_health"`, one record `society_of_killers` → `health: "healthy"`,
  `issue_counts {healthy:1,…,total:1}`. **Expect publisher:** `projection: "publisher_health"`, `edenseek`
  → `health: "healthy"`. No-auth → 401.

### D4 — Coherence + boundary + scheduler continuity
- Engineering session independently recomputes issue/series/publisher health from the live Registry and
  confirms the endpoints match + `publisher == roll_up(all issues)` (recomputable-from-below).
- Confirm the next scheduled Registry rebuild fires normally and writes only `edenseek-scout`.

## 4. Evidence to record
`/health`; `/observability/health` (unchanged) + `/registry` 401; the two new authed bodies + their 401s;
the `registry rebuild` registration line; the coherence recomputation.

## 5. Deliverable
`INCREMENT_2_DEPLOYMENT_CERTIFICATION_REPORT.md` — per-criterion (D1–D4) evidence + PASS/FAIL + verdict.

## 6. Rollback / safety
- Rollback = `git checkout 4857ed2` + restart — code-only, immediate; `.env`/IAM unchanged.
- Increment 2 is additive + read-only (advisory); no new write, no Publisher access; scheduler/Registry/audit
  path untouched.

---

*Plan only — production is not touched by this document. Await founder review before deploying.*
