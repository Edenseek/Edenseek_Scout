# ATLAS_RESUME.md — resume note for the next Scout (Atlas) session

> **You are Atlas**, the Claude Code session that works the `Edenseek_Scout` repo. This is your own
> hand-off note. Your persistent **memory** (`MEMORY.md` + the memory files) auto-loads each session and
> carries the fine detail; this file is the single **operational entry point** so you re-orient fast.
> **Last updated:** 2026-08-13 · **main @ `e2a23b2`** (+ `SUMMARY.md`/this note on top) · **suite: 501 green.**

---

## First 90 seconds on resume

1. `git pull`.
2. Read **`SUMMARY.md`** (repo root) — the full status; and skim your **`MEMORY.md`** index.
3. **Check the bridge:** `ls -t publisher_bridge/*.md | head`. The newest **Johnny** note (not one of your
   own `responses/…`) is the live signal. As of this note the last exchange was the **intake-seam close
   (3/3 PASS)** — nothing pending either direction.
4. Then act on whatever the bridge / Derek gives you (see "Triggers" below). If nothing new, there is nothing
   to build — say so; do not invent work.

## Who's who / how work flows (do not forget this)

- **Atlas = you** (this repo, the read-and-advise audit sidecar). **Johnny** = the Publisher session
  (`edenseek-publishing`/`edenseek-intelligence`). **Keystone** = human oversight/priority authority.
- Coordination is **only** through `publisher_bridge/` git notes: Johnny writes to the root, you reply under
  `publisher_bridge/responses/`. **You have no direct channel to Johnny — Derek relays; each side pulls.**
- **Derek runs all production commands** (`ADR-0002`: production S3 needs `SCOUT_RUNTIME_MODE=production`;
  you cannot read production from a dev session — never assume you can). You never SSH the VM.

## Non-negotiable working discipline (this is how everything here was built)

- **Charter first:** read-and-advise only. Never modify Publisher data, approve/set state, self-modify
  scoring, or bypass human approval (`SCOUT_CHARTER.md` §4). Writes go only to `edenseek-scout`.
- **Certified-first, every change:** build → **dispatch an adversarial review** (a general-purpose agent on
  the branch diff) → **fold findings + re-verify** → write a `docs/phases/<name>/CERTIFICATION_REPORT.md` →
  merge to `main` → push → Derek deploys → **two-party live-cert with Johnny** via the bridge. Small,
  obvious fixes may get a documented self-review instead of a full agent round — match rigor to risk.
- **Versioning rule:** a metric/methodology change must move BOTH the comparability axis
  (`scout_report_index`) AND the ledger fingerprint (`scout_delta_audit.static_versions`), or a re-audit
  silently skips/collides.
- **Principles:** P1 (Publisher emits facts, Scout derives observations), P2 (recompute-from-below). Prefer
  a Publisher-emitted **fact** over Scout **inferring** things (e.g. "this issue is a duplicate").
- **Bridge etiquette:** when you finish/decide something, write the bridge note + commit + push so Johnny
  can pull. Acknowledge his findings plainly; his S3-state observations are strong, his runtime "why"
  guesses are weaker (he can't see your logs) — corrected this explicitly on the `sample_sizes` episode.

## Current state: everything is CLOSED (nothing mid-flight)

Merged + certified + (where live) two-party verified: **Metadata Accuracy v3 + low-confidence marker**
(first real accuracy number 0.763), **SXI-2 multi-issue dashboard 2a–2e (6/6)**, **manual-publication
truthfulness** (F1 severity + F4 findings viewer), **rebuild visibility + `sample_sizes` fix**, and the
**intake seam** (multi-issue dataset audit — every issue now gets a consolidated `scout_report_`). See
`SUMMARY.md` §2 and the per-increment `docs/phases/…` cert reports.

## ⏸ The one directive that gates the next work

**Derek, 2026-08-13:** *"it's ok to let metrics slightly skew as we are still testing the platform… once we
have the pipeline ironed out then we will begin a more rigorous and careful process to give scout better
metrics."* → During the testing phase, **tolerate minor metric skew; do NOT build metric-precision
refinements** on your own. Correctness/safety/Charter bugs are still fixable. See memory
`testing-phase-tolerate-metric-skew`.

## Triggers (what to do when X happens)

- **Derek says "begin the rigorous metric pass"** → the tolerance lifts. Start the queued metric work
  certified-first, in this order: **CBI-4 v2 consumption** (materials_grounding v1/v2 comparability boundary
  + `content_included` surfacing — field shapes confirmed in memory `supporting-materials-future-audit-surface`;
  v2 data exists on `caelaris/promises` #2) → **duplicate/experimental-control exclusion** (spec a
  Publisher-emitted `exclude_from_aggregates` flag; `promises` #2 is the duplicate skewing aggregates) →
  **precision-vs-recall acceptance refinement** → **`review_record_id` full-identity sibling**.
- **Johnny publishes the materials-arm regeneration** of `caelaris/promises` (materials grounding on,
  Registry off) → run the audit and report the **paired before/after** vs the 0.763 / 44-empty-`characters`
  baseline (44 is the number to beat). This is also the CBI-4 `v2` live-cert data.
- **Johnny posts any new bridge note** → read it, advise Derek, and run the certified-first cycle if it's a
  Scout build.
- **A new metric/methodology anomaly appears** → if it's *metric skew* in the testing phase, flag it as
  expected, don't chase it. If it's a *correctness* bug (wrong data, broken seam, Charter breach), fix it.

## Where the detailed truth lives

- Full status: **`SUMMARY.md`**. Per-increment certs: **`docs/phases/*/CERTIFICATION_REPORT.md`**.
- Governance: **`SCOUT_CHARTER.md`** (authoritative), `docs/architecture/ADR-0001` (observability arch),
  `ADR-0002` (runtime safety). ⚠ `CLAUDE.md` + `scout_status_and_tech_debt.md` are **behind reality**
  (still say "Memory v0.4 / June 2026") — reconciling them is logged debt, worth an early pass.
- Your memory index: **`MEMORY.md`** — every track above has a memory file with the specifics.
