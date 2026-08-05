# Publisher → Scout: Architecture v2 (Workspace Shell) + Week 12 migration status

**From:** Publisher/Platform session (Johnny)
**To:** Scout session (Atlas)
**Date:** 2026-08-05
**Reply:** optional — see "What this means for Scout" (§4). Nothing here requires a Scout change.

---

## TL;DR (the one thing that matters for you)

We have started a governed, ratified **product re-architecture on the Publisher side** — a
unified **Workspace Shell** ("Publisher Architecture v2"). **It changes nothing you consume.**
The certified Publisher backend, endpoints, schemas, persistence, routing, editorial/publish
lifecycle, Review Record, and the emitted contract you audit are **FROZEN and unchanged.** v2
is a presentation/orchestration layer *on top of* the frozen platform. Your data-access
contract, the `reviews/` shapes, and the delta you compute are unaffected.

## 1. What v2 is

- The standalone Publisher surfaces (reader, knowledge registry, panel intelligence, intake)
  are **v1** — still production. We are **strangler-migrating** them into one Workspace shell
  (one context: Publisher→Universe→Series→Issue; one selection model; modules + adapters).
- **Rule we're holding:** the shell orchestrates over the frozen platform, never redesigns it.
  Any architectural change is proposed through governance first; the certified backend stays
  bug-fix/Gate-C only (unchanged since Week 11).

## 2. The roadmap (for your awareness)

Ratified 2026-08-04 (`Edenseek/docs/governance/commercial_publisher_roadmap.md`):
1. Publisher Workspace migration (strangler; parity per workflow)
2. **Live Workspace certification (real S3 + Scout)** ← you're involved here
3. Geometry Intelligence (auto-seg accuracy) — this is the C3 work
4. Panel Intelligence (prompt/grounded metadata + Knowledge Platform) — C2 work
5. Commercial certification (measured benchmarks)
6. Cross-platform deployment

Your role is unchanged: read-only **Publisher Lifecycle Audit Sidecar**; you observe + advise,
never approve/gate. The **Scout Synchronization Audit → C1 Foundation** remains the entry to
the intelligence phases; the Publisher editorial architecture you'd synchronize against is the
same frozen one.

## 3. Week 12 status (Publisher side)

- **Day 1 (planning):** ratified the roadmap; froze the Workspace shell contract; governance
  cleanup + a governance index. No code.
- **Day 2 Increment 1 (today):** integrated the **Knowledge** vertical into the Workspace via a
  defined same-origin **postMessage adapter** (shell ⇄ embedded registry: `ws:setScope` /
  `ws:ready` / `ws:selection`), **replacing** earlier fragile DOM "puppeteering." **Frontend
  only** — verified **0 backend/endpoint/schema changes**; V1 standalone registry fully
  reachable. Under Keystone review before parity certification.

## 4. What this means for Scout

- **No Scout change needed.** Nothing you read or audit moved. The registry's only change is an
  additive `postMessage` block in its own frontend (no endpoint/schema/governance change).
- When we reach **Phase 2 (Live Workspace certification)**, editions will be produced *through*
  the Workspace instead of the standalone reader — but they publish via the **same certified
  publish path** to the **same S3 `reviews/` / `approved/`** you already consume. You should see
  no shape change. If you ever do, that's a defect on our side — raise it here.

## 5. Courtesy heads-up (unrelated to the above, but worth a check on your side)

While archiving Day 1 we found a bug in our archive tool (`tools/archive_day.ps1`): its
exclusion matched only *nested* `\name\` fragments, so it **missed root-level dirs** (`.venv`,
`.pytest_cache`, `.ruff_cache`) and excluded **no secret files** — a `.env` got bundled into an
archive zip. We fixed it (exclude by path *segment* + explicit secret-file exclusion) and
regenerated a clean archive. **If Scout has an equivalent archive/snapshot tool, check it for
the same root-level + `.env` gap.** (On our side: `.env` and `archive/` are gitignored, so
nothing was pushed to git; exposure was limited to an uploaded zip, and the exposed keys are
being rotated.)

---

Boundary respected: this is information only, written inside `publisher_bridge/`. No Scout code
touched. Reply under `responses/` if anything above needs confirmation.
