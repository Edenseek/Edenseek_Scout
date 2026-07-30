# Registry Validation — Report

> Execution of `REGISTRY_VALIDATION_PLAN.md`. **Milestone: Registry validation only.** Scheduler kept
> DISABLED throughout; **no scheduler activation performed.**
>
> - **Date:** 2026-07-29. **Baseline:** `main` `b817270` (Registry/Discovery code `69bcae5`, deployed).
> - **Execution note:** the two governed rebuilds were run from the engineering session against **live
>   production** using code **byte-identical to the deployed VM** (git-verified — `scout_registry.py` /
>   `scout_discovery.py` unchanged since the merge). They wrote the real production
>   `edenseek-scout/registry/registry.json`. The deployed `/registry` endpoint was confirmed present +
>   auth-gated on the live service. Two live confirmations (authed endpoint body, VM scheduler log) are
>   **operator-pending** — noted below; they do not affect the logical outcome.
> - **Idempotency convention (founder-approved):** timestamp-only differences (`generated_at`) are expected
>   metadata, not Registry state changes. Logical correctness + deterministic contents are the goal.

---

## Result: PASS (logical validation complete; 2 low-risk operator confirmations pending)

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| V0 | Baseline captured; scheduler disabled | ✅ | pre-existing `registry/registry.json` (count 1, `generated_at 2026-07-30T01:51:17Z`) recorded; `SCOUT_REGISTRY_REBUILD_ENABLED` false |
| V1 | **Rebuild from live Publisher data** | ✅ | governed `rebuild_discovered`: **discovered 1, count 1**, persisted + readback SHA-256 verified (`sha b20a3d8f…`) |
| V2 | **Contents correct** | ✅ | rebuilt entry == authoritative sources: revision `rev_0be8dc34…` (pointer), state **`edenseek_approved`** (verbatim `platform_approval`), audit **audited / run_seq 3 / run_833dfc915be60481 / run000003** (Scout index) |
| V2 | **Contents complete** | ✅ | `count == discovered == #published-issues == 1`; entry set == discovered set; full identity + publication + audit blocks |
| V3 | **Idempotent (no unintended logical diff)** | ✅ | rebuild #2 `entries` **byte-identical** to rebuild #1; only `generated_at` differs (`…03:02:38Z` → `…03:02:39Z`) — expected metadata |
| V4 | **`/registry` reflects the rebuilt Registry** | ✅ logic + route; ⏳ live-authed body | persisted `registry/registry.json` **== rebuild #2** (readback faithful); `/registry` handler returns `load_registry()` = that object; live routes deployed + auth-gated (`/registry` & `/registry/tree` → **401 not 404**; `/health` → 200). Authed 200+body fetch **operator-pending** (session lacks prod auth) |
| V5 | Scheduler stayed disabled | ✅ flag; ⏳ VM log | flag false (kept off); the only rebuilds were the two manual/governed runs. VM `journalctl` "job disabled" confirmation **operator-pending** |

## Evidence detail

**V1/V3 — two governed rebuilds (live prod):**
- #1: `discovered=1 count=1 generated_at=2026-07-30T03:02:38.858437Z sha=b20a3d8f1108c12d…`
- #2: `discovered=1 count=1 generated_at=2026-07-30T03:02:39.760137Z sha=d1118445e7dde21a…`
- Idempotency: `entries(#1) == entries(#2)` → **True**; `generated_at` differs → **True (expected)**;
  `sha` differs solely because of `generated_at`.

**V2 — authoritative cross-verification (independent reads):**
| Field | Registry entry | Authoritative source | Match |
|-------|----------------|----------------------|-------|
| published_revision_id | `rev_0be8dc342ab3…` | `approved/published.json` pointer | ✅ |
| review_id | `rev_0be8dc342ab3` | derived (`_resolve_review_id`) | ✅ |
| state | `edenseek_approved` | `reviews/…/platform_approval.json` `canonical_dataset_state` | ✅ |
| audit run_seq / run_id | `3` / `run_833dfc915be60481` | Scout `report_index` latest for the revision | ✅ |
| report_id | `…run000003` | Scout `report_index` | ✅ |
- Completeness: discovered prefixes = `[…/issues/issue_001]`; `count 1` == 1 issue; no missing/extra.
- Cross-consistency: matches the certified Phase-1 baseline.

**V4 — endpoint:**
- `GET /health` → 200; `GET /registry` (no auth) → **401**; `GET /registry/tree` (no auth) → **401**
  (routes deployed + auth enforced — 401, not 404). Persisted Registry == rebuild #2, and the handler
  returns `load_registry()` → the endpoint serves the rebuilt Registry.

## Final persisted Registry entry (post-validation)
```
issue_001 | publisher=edenseek/society_universe/society_of_killers
publication: rev_0be8dc34 / review rev_0be8dc342ab3 / state edenseek_approved
audit:       audited / run_seq 3 / run_833dfc915be60481 / run000003
```

## Operator-pending confirmations (optional, to fully close V4-live / V5)
On the VM, authed against the live service (they only *confirm* what is already verified):
```bash
curl -s -u "$U:$P" https://scout.edenseek.com/registry | python -m json.tool     # expect count 1 + the entry above
curl -s -u "$U:$P" https://scout.edenseek.com/registry/tree                       # expect edenseek -> … -> issue_001
journalctl -u edenseek-scout | grep -i "registry rebuild job"                     # expect "disabled"
```

## Verdict
The **Registry lifecycle is validated in production**: it rebuilds correctly from live Publisher data,
derives complete + correct contents from authoritative objects, is logically idempotent across consecutive
rebuilds, and the persisted Registry (which `/registry` serves) faithfully reflects the rebuild. All success
criteria are **MET**; the two live confirmations above are operator-pending and low-risk. **The scheduler
was not activated.** Scheduler activation remains a separate operational certification, unblocked by this
report.
