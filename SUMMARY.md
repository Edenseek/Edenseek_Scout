# Edenseek Scout — Project Status & Resume Summary

> **For Derek, returning ~2026-09-03 after ~3 weeks away.**
> **As of:** 2026-08-13 · **main @ `e2a23b2`** · **test suite: 501 passing** · working tree clean, all pushed.
> This is a point-in-time handoff. Where it conflicts with `SCOUT_CHARTER.md`, the Charter wins.

---

## 0. TL;DR

Scout is healthy, deployed, and at a **clean, fully-certified stopping point**. Over the last stretch we took
Scout from single-issue to **multi-issue across the whole publisher** (4 issues in 3 "universes"), shipped a
**multi-issue dashboard (SXI-2)**, got the **first real metadata-accuracy number in the project's history**
(0.763, in the target band), and **closed the Scout→Edenseek intake seam** so Publisher Diagnostics works for
every issue. Everything was built under **certified-first** discipline (build → adversarial review → fold →
certify → merge → deploy → two-party live-cert with the Publisher session).

**Nothing is mid-flight.** The next work is **paused on purpose** until you signal the platform pipeline is
"ironed out" (your directive — see §3). Until then we tolerate minor metric skew.

---

## 1. How Scout is built + coordinated (read this first to re-orient)

- **What Scout is:** a **read-and-advise Publisher-Lifecycle-Audit Sidecar** (`SCOUT_CHARTER.md`). It inspects,
  scores, explains, recommends — it **never** modifies Publisher data, approves content, becomes the source of
  truth, self-modifies its scoring, or bypasses human approval. Every change this cycle stayed inside those
  boundaries.
- **Two repos, two sessions, one bridge:**
  - **This repo = `Edenseek_Scout`** (the audit sidecar). My session is **"Atlas."**
  - **`edenseek-publishing` / `edenseek-intelligence`** (the Publisher). A separate Claude session is
    **"Johnny."**
  - **`Keystone`** is the human/oversight authority for priority & sequencing.
  - We coordinate through `publisher_bridge/` (git-synced notes; Johnny's under the root, my replies under
    `publisher_bridge/responses/`). **I have no direct channel to Johnny — you relay, and each session pulls.**
- **Two guardrail ADRs:** `ADR-0001` (repo-ownership / observability architecture — Discovery→Registry→Audit→
  Publication, frozen) and `ADR-0002` (runtime-safety boundary — production S3 requires
  `SCOUT_RUNTIME_MODE=production`; my dev session **cannot** read production, so **you run all production
  commands on the VM**).
- **Two report families:** the **consolidated `scout_report_`** (the dataset/retrieval audit — the ratified
  governance/Diagnostics contract Edenseek intake ingests) and the **`scout_delta_report_`** (generated-vs-
  approved delta — Scout's own analytical artifact for its dashboard).

---

## 2. ✅ What was completed (this cycle — all merged, certified, deployed)

Each was adversarially reviewed and, where it touched live data, two-party verified by Johnny.

| # | Deliverable | What it does | Live status |
|---|---|---|---|
| 1 | **Metadata Accuracy v3** + `low_confidence_no_inspection` marker | Revision-aware acceptance denominator (origin-composite); the marker flags a bulk-approved 100% | **Live-certified** on `caelaris/promises` #1 — **0.763 (297/389)**, the first non-vacuous accuracy number ever; marker certified by correctly *not* firing (founder actually edited) |
| 2 | **Dashboard truthfulness hotfix** (§1/§4) | Multi-issue "Run Delta Audit" button; surfaced the low-confidence marker | Live |
| 3 | **SXI-2 (multi-issue dashboard), 2a–2e** | Issue picker · Universe hierarchy + cross-series · per-scope benchmarks + comparability guard · series-vs-series · post-audit auto-refresh | **6/6 live cert** across 3 universes (composite view deferred per Keystone) |
| 4 | **Manual-publication truthfulness** (F1 severity + F4 findings viewer) | A not-yet-platform-approved revision no longer shows a false FAIL (→ `platform.approval` WARNING); you can finally see *why* a report has its severity | Live-verified |
| 5 | **Rebuild visibility + `sample_sizes` identity fix** | A silently-failing projection rebuild now shouts; distinct-issue counting fixed (was collapsing on the bare `issue_001`) | Verified 3/3 |
| 6 | **Intake seam — multi-issue dataset audit (Option A)** | Every discovered issue now gets a consolidated `scout_report_` under its own prefix → Publisher **Diagnostics populates for every issue** (was blank for new ones); folded into `--all` | **Closed, 3/3 verified** — Scout produces → intake ingests → Diagnostics shows, zero code change on Edenseek's side |

**Operational reality:** one command — `SCOUT_RUNTIME_MODE=production venv/bin/python scout_delta_audit.py
--all` — now audits every published issue (delta), produces every issue's consolidated report, and refreshes
the derived Registry + benchmark projections. Idempotent (skips unchanged issues), per-issue isolated,
non-fatal on the derived-refresh steps.

**Current published surface:** 4 issues across 3 universes — `society_universe ▸ society_of_killers`,
`caelaris ▸ promises` (#1 and #2), `i_ride_for_them ▸ i_ride_for_them`. (`promises` #2 is a deliberate
*duplicate* grounding-experiment control — see §3.)

---

## 3. ⏸ What's outstanding (deferred on purpose — nothing is stuck)

**Your standing directive (2026-08-13), which gates most of this:** *"it's ok to let metrics slightly skew as
we are still testing the platform… once we have the pipeline ironed out then we will begin a more rigorous and
careful process to give scout better metrics."* So the items below are **logged and paused**, not blocked.
When you're back and say the pipeline is stable, that's the signal to start the **rigorous metric pass**.

### A. Queued Scout work (build on your "pipeline ironed out" signal)
- **CBI-4 `v2` materials-grounding consumption** — treat `materials_grounding_version` v1/v2 as a comparability
  boundary (don't pool) + surface the new `content_included` / `omitted` fields ("named but not read"). Field
  shapes are confirmed and logged; `v2` data now exists (`promises` #2).
- **Duplicate / experimental-control exclusion** — `promises` #2 currently skews platform/publisher aggregates
  (`sample_sizes.issues` reads 4, one book double-counted). Fix = a Publisher-emitted `exclude_from_aggregates`
  flag Scout consumes. **You chose to tolerate the skew for now.**
- **Precision-vs-recall acceptance refinement** — the grounding experiment showed the model made *zero wrong*
  character names; the whole gap is *recall* (missed). An acceptance rate alone can't tell "wrong" from
  "incomplete." Motivating case is logged.
- **`review_record_id` full-identity sibling** — the bare-leaf `issue_001` collides *across* series; add an
  additive `publisher·universe·series·issue` field (Johnny will adopt without a coordinated release).

### B. Waiting on the Publisher (Johnny) — Scout will measure when they land
- **Materials-grounding before/after** — Johnny will regenerate `caelaris/promises` with *materials grounding
  only* (Registry off, arms separable); Scout reports the paired delta vs the 0.763 / 44-empty-`characters`
  baseline. **44 is the number to beat.**
- **METRIC-1 bulk-approve signal** — the one prerequisite still owned by the Publisher; until it exists, the
  marker's `rate==1.0 & 0-edits` heuristic is the proxy for "approved without inspection."
- **Intake trigger** — auto-run intake after a Scout write vs manual; Edenseek's decision (part of their
  "three manual UI-less steps" onboarding finding).

### C. Logged Scout tracks (no external dependency, low priority)
- **Phase-3 rev-to-rev editorial-burden** — measure editorial change *across revisions* (the delta family only
  sees within-revision generated-vs-approved; a human improving a revision currently reads as "nothing
  happened").
- **spread_order reading-order axis** — data is published; read it from the published approved geometry (it's a
  manual publication, so it won't arrive via the delta family). Base64 location noted in the bridge.
- **Detector generalization** — `promises` is the first book outside the geometry detector's cert corpus (its
  worst result yet: precision 0.68 / recall 0.26) → a `detector_version`/`detector_config` datum.
- **Perf follow-ups** — uncached whole-bucket scan on scoped `/intelligence/*`; double-Discovery on `--all`.
  Both correctness-neutral; revisit as issue count grows.
- **`audit_ready` / `objects_missing` required-scoping** — latent (no consumer renders them today).
- **Track A materials-resolution auditor** — offline-certified; live cert parked.

---

## 4. Where we are vs the governing docs (Charter, ADRs, roadmap)

**Boundaries (Charter §4) — fully respected.** Everything shipped is read-and-advise: Scout reads the
Publisher repo GetObject-only (IAM-denied writes), writes only `edenseek-scout`, never approves/sets state,
never self-modifies scoring. ADR-0002's production gate held throughout.

**Principles (Charter §5) — actively applied.** P1 (Publisher emits *facts*, Scout derives *observations*) and
P2 (recompute-from-below: every projection is a deterministic function of the layer beneath) drove the whole
multi-issue + dashboard design. Versioning discipline (a methodology change must move both the comparability
axis *and* the ledger fingerprint) was used on every metric version bump.

**Charter §8 Product Roadmap:** Phases 1–2 (Dataset + Publisher Intelligence) are ✅; the doc lists **Phase 3
(Dataset Failure Analysis) as the "current active phase"** with Phases 4–7 ahead. That linear
"dataset-intelligence-depth" roadmap is **one axis**; the actual driving work this cycle has been a **second
axis** — the **cross-repo Publisher-Lifecycle observability architecture (ADR-0001)**: multi-issue Discovery →
Registry → per-scope Health/Benchmark/Intelligence → the delta-audit family → the dashboard → the intake seam.
Both coexist and both stayed inside the Charter.

**⚠ Documentation drift (flagged as tech debt in `CLAUDE.md` itself):** the top-level status docs are **behind
reality.** `CLAUDE.md` still reads *"Production Alpha · active milestone Memory v0.4 · last verified fdf0ab8 ·
June 2026"* — that predates the entire multi-issue / dashboard / metadata-v3 / intake-seam arc. **A worthwhile
early task on return:** reconcile `CLAUDE.md`, `scout_v0.3_synopsis.md`, `scout_status_and_tech_debt.md`, and
the Charter §8 "active phase" line with the actual state (the per-increment cert reports under
`docs/phases/…` are the accurate record). This isn't urgent, but it's real debt.

---

## 5. How to resume (first actions on return)

1. **Re-read this file, then `SCOUT_CHARTER.md` §4–§5** (boundaries + principles) to re-anchor.
2. **`git pull` and check the bridge:** `ls -t publisher_bridge/*.md | head` — the newest Johnny note tells you
   what's new. As of now the last exchange is the **intake-seam close (3/3)**; nothing is pending in either
   direction.
3. **Decide the trigger:** if the platform pipeline is now stable, tell me *"begin the rigorous metric pass"* —
   that lifts the testing-phase tolerance (§3) and we pick up the queued metric work (start with CBI-4 v2
   consumption + duplicate exclusion, since the v2 data and the skew both already exist).
4. **If Johnny has published the materials-arm regeneration** (or anything new), that's a Scout build/measure
   trigger — hand me the note and I'll run the certified-first cycle.
5. **The per-increment truth is in `docs/phases/…/CERTIFICATION_REPORT.md`** — each deliverable in §2 has one.
   Memory (my persistent notes) also carries the fine detail; I'll recall the relevant pieces automatically.

**Key production commands (you run these on the VM — ADR-0002):**
- Full multi-issue cycle: `SCOUT_RUNTIME_MODE=production venv/bin/python scout_delta_audit.py --all`
  (audits every issue + consolidated reports + refreshes projections; the result JSON now carries `dataset`
  and `rebuild` blocks — a `failed:` in either now also logs a WARNING + prints to stderr).
- Deploy: on the VM, `git pull` → `sudo systemctl restart edenseek-scout`.
- Dashboard: `https://scout.edenseek.com/dashboard` (Operations · Engineering · Intelligence; the Intelligence
  tab now has the issue picker, Universe column, cross-series panel, and series-comparison table).

---

## 6. One-line health check

Deployed and healthy · suite 501 green · main `e2a23b2` pushed · bridge quiet, all threads closed · no
mid-flight work · next move is yours (the "pipeline ironed out" signal). Enjoy the vacation.
