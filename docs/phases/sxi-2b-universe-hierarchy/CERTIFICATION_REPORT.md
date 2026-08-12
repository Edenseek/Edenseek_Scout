# Certification Report — SXI-2b (Universe / title-group hierarchy + cross-series health)

**Track:** Scout Expansion Increment 2 · sub-increment **2b** (the §3 hierarchy fix)
**Branch:** `week12-sxi2b-universe-hierarchy`
**Date:** 2026-08-12 · **Discipline:** certified-first (build → adversarial review → certify → deploy → verify)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for merge → deploy

---

## 1. What changed and why

Johnny's SXI-2a walkthrough (§3): the dashboard rendered `Publisher → Series → Issue` and skipped the
**title group / Universe** level, so `society_universe`'s series and the `i_ride_for_them` universe read as
two unrelated names at the same depth — and would get worse as a universe gains more series. SXI-2b surfaces
the Universe level. Per Keystone's ratified decisions: **label "Universe"** to humans, keep `title_group_id`
as the identifier in data/APIs, **display-only grouping** (no `title_group_health` rollup — 2 of 3 universes
hold exactly one series today).

Pure **front-end surfacing** over data that already exists — `title_group_id` is on every health record and
on the report's `issue_identity`; `/observability/health/cross-series` is already served. No server change,
no contract change, read-only.

## 2. Changes (`static/index.html`)

- **Identity strip (`geomSummary`)** — a `Universe` cell reading `ii.title_group_id` between Publisher and
  Series, so the strip reads `Publisher · Universe · Series · Issue · Measured · Geometry`. Graceful `—` when
  absent.
- **Operations → Publisher Health (`opsPubHealth`)**
  - **Universe column** on the Series table (`["Universe","Series","Health","Issues healthy","Issue IDs"]`)
    and the Issues table (`["Universe","Series","Issue","Health","Publication state","Reasons"]`), sourced
    from each record's `title_group_id`. `society_universe ▸ society_of_killers` now reads as a hierarchy.
  - **Cross-series panel** — surfaces the already-served-but-unwired `/observability/health/cross-series`:
    the platform-wide series distribution (`summary`) + the **attention set** (`attention[]`, series whose
    health ≠ healthy), each row `Universe ▸ Series — n/N issues healthy`. Fetched **tolerantly** (its own
    `try/catch`, `xs=null` → panel omitted) so a cross-series failure never breaks the primary Publisher
    Health panel.

## 3. Boundary / safety

Read-only. Every server-controlled field (`title_group_id`, `series_id`, `issue_id`) is `esc`'d; the
cross-series `.att li` class uses a mapped health→severity string, not a raw value. No new endpoint, no
write. Display-only grouping — no new projection or rollup (per Keystone Q3).

## 4. Verification

Full suite **467 passed** (unaffected — front-end only). Dashboard JS `node --check` clean. The consumed
endpoints (`/observability/health`, `/series`, `/publisher`, `/cross-series`) are already covered by the
observability tests; SXI-2b adds no server logic to test.

## 5. Adversarial review (one round + fold)

**Verdict: safe to merge + deploy — all six concerns pass, no MAJOR/MINOR functional defects.** The reviewer
verified against the server shapes that:
- The cross-series panel reads the actual `cross_series_health` shape (`summary`/`attention[]`), never a
  phantom `.records`; every field accessed (`title_group_id`, `series_id`, `issue_counts.healthy/total`,
  `health`) exists on the attention elements (full series_health records).
- Null handling is correct (`|| "—"`, `(a.issue_counts||{})`), and the tolerant `xs=null` path cleanly omits
  the panel with no error and no effect on the primary panel.
- Every server-controlled field is `esc`'d; the `.att li`/`.sev` classes use a mapped severity literal, not a
  raw value — no XSS.
- Both new tables' headers and row arrays match exactly (5 and 6 columns) — no off-by-one.
- The 6-cell identity strip is a wrapping flexbox — no positional assumptions, no regression.
- The cross-series `.att li` matches the grid convention (bare `sev` span first, wrapper div second).

Two cosmetic NITs; one folded, one accepted:

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | NIT | The "derived from" footer always credited `/cross-series` even when that fetch failed and the panel was omitted. | **Fixed** — the `/cross-series` credit is now conditional on `xs`. |
| 2 | NIT (pre-existing) | Row cells are `esc`'d in serRows/issRows and re-`esc`'d by `rows()` (double-escaping). | Accepted — safe over-escaping, not introduced here; real IDs carry no special chars. |

## 6. Certification statement

Additive, read-only, display-only surfacing of already-certified Registry-derived data; labels the level
"Universe" while keeping `title_group_id` as the identifier; no rollup, no server or contract change.
Adversarial review found no functional defect; the one introduced NIT is fixed. Suite **467 passed**, JS
`node --check` clean. **Offline-certified.** Remaining gates: merge → deploy (`git pull` + restart) → verify
the Universe cell/columns render and the cross-series panel lists the attention set.
