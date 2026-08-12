# Atlas → Johnny + Keystone: Scout Expansion **Increment 2** (multi-issue dashboard) — SCOPE FOR APPROVAL

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform) + Keystone (supervisor). **Date:** 2026-08-12.
**Status:** SCOPE ONLY — **no Scout code will be written until this is approved.** Trigger: Johnny's
`2026-08-12_publisher_dashboard_walkthrough_inc1_invisible_and_no_title_group.md` (§2 reachability, §3 no title-group level).

> Bridge ground rule honoured: this note is the only thing written here; no Publisher code touched.

---

## 0. Naming — avoid the collision

This is **Scout Expansion Increment 2** (the all-books *dashboard* increment from the approved capability
plan: issue picker, per-series, series-vs-series, composite, title-group hierarchy). It is **NOT** the D8
health-projection "Increment 2/3," which is already built and deployed (series/publisher/cross-series
health rollups). Different track, unfortunate number reuse — I'll call mine **SXI-2** below.

## 1. The headline finding: SXI-2 is ~80% surfacing, not new computation

I mapped the whole stack before scoping. Almost everything SXI-2 needs **already exists server-side and is
simply not wired into the dashboard.** Inventory:

| Capability | Server-side state | Wired to UI? |
|---|---|---|
| Registry spanning ALL issues, `title_group → series → issue` rollup + tree | **Built** — `scout_registry.rebuild_discovered`, `rollup`, `tree_view`; served at `GET /registry/tree` | ❌ never fetched |
| Issue / Series / Publisher / **Cross-series** health | **Built** — all 4 in `scout_observability.py`; 4 endpoints | issue/series/publisher ✅; **cross-series ❌** |
| Per-scope benchmarks (issue/series/publisher/platform), persisted per level | **Built** — `scout_benchmark.rebuild_all` writes a benchmark.json at every level | `GET /benchmark/{level}` serves **platform only**; series/publisher/issue persisted but not served |
| Geometry / Metadata Intelligence with a `scope` param | **Built + scope-capable** — `scout_intelligence.py`; endpoints exist | loaders **hardwired to the single env issue**; not consumed by UI |
| Full `publisher/title_group/series/issue` identity on every index/registry/context record | **Built** — carried everywhere | identity strip shows only Publisher→Series→Issue |
| Report archive across ALL issues | **Built** — `/audit-review/archive` is global, newest-first | picker lists them but options **don't show which issue**; analytics pin to the global `/reports/latest` |

**So the §2/§3 gaps are front-end wiring + a few small server completions, not a rebuild.** This is the
"recompute-from-below / surface what's already certified" posture (P2), and it keeps Scout read-only and
advisory — the UI is observability over the agent, never new business logic.

## 2. Boundary (reaffirmed)

- **No Publisher contract change and no Publisher work required.** `title_group_id` is already in the S3
  prefix Scout reads (`publishers/{p}/title_groups/{tg}/series/{s}/issues/{i}`) and is captured by Discovery
  → Context → Registry → index entries. SXI-2 surfaces data Scout already has.
- Scout stays read-and-advise: all new endpoints are GET projections over persisted Scout artifacts; all new
  UI is read-only. No writes to Publisher data, no approval authority.
- Everything numeric that gets aggregated across issues/series obeys the **comparability guard** (§4).

## 3. Sub-increments (each its own certified-first cycle: build → 2 adversarial rounds → cert → deploy → verify)

**SXI-2a — Issue picker + issue-labelled report selector (the §2 fix).** *Front-end-heavy, tiny server.*
Add an issue/series **picker** to the analytical views; label each report-selector option with its
`series_id / issue_id` (already on every archive record) so distinct issues stop being indistinguishable;
make the analytical views resolve *"latest for the selected issue"* instead of the single global
`/reports/latest`. Small server helper: "latest report for a given `issue_prefix`" (or client-side filter of
the global archive by `issue_id`). *Files:* `static/index.html` (selector/`reportBar`, `render` dispatch),
`app.py` (+1 small endpoint or query param). *Risk:* low. Highest founder value — this alone kills "Scout
didn't see the IRFT publication."

**SXI-2b — Title-group ("Universe") hierarchy + cross-series surfacing (the §3 fix).** *Front-end + one small
optional projection.* Wire the already-built `GET /registry/tree` into the dashboard to render
`publisher → title_group → series → issue`; add the title-group level to the identity strip (between
Publisher and Series). Surface the already-served-but-unwired `cross_series_health`. *Optional:* add a
`title_group_health(registry)` rollup (data is present on every record; it mirrors `series_health` — a
~10-line additive pure function) if we want a title-group health level, not just a display grouping. *Files:*
`static/index.html`, optionally `scout_observability.py` (+1 pure fn + 1 route). *Risk:* low.

**SXI-2c — Per-scope benchmark serving + cross-issue Intelligence loaders + the comparability guard.**
*Server-side completion.* (1) Complete `GET /benchmark/{level}` for `publisher/series/issue` — the objects
are already persisted by `rebuild_all`; this is serving, not computing. (2) Add cross-issue Intelligence
loaders: enumerate indexes via the existing `scout_benchmark.discover_issue_indexes`, merge entries, and call
the already-scope-capable `geometry_intelligence` / `metadata_intelligence` with the requested scope; add a
`scope`/issue selector to the two `/intelligence/*` endpoints. (3) Enforce the comparability guard (§4) on
every cross-scope aggregation. *Files:* `app.py`, `scout_intelligence.py` (loaders only — the projection
functions already take `scope`), tests. *Risk:* medium (correctness of aggregation — hence its own adversarial cycle).

**SXI-2d — Series-vs-series + composite/overall views.** *Front-end + one compare endpoint.* This is the
genuinely new piece: the benchmark builder aggregates *into* one scope; it does not produce a
compare-N-scopes view. Add a view that places N series/issues side-by-side (their per-scope benchmark +
health), and a **composite/overall** top view (platform benchmark + publisher health, both already built).
Either a small `/benchmark/compare?scopes=…` endpoint or the front-end fetches per-scope `/benchmark/{level}`
N times and composes. *Files:* `static/index.html` (+1–2 new render fns + tab), `app.py` (maybe +1 endpoint).
*Risk:* low-medium. Depends on 2c.

**SXI-2e — Registry-rebuild freshness (prerequisite, small).** Everything multi-issue is only as complete as
the persisted Registry. `rebuild_discovered` exists and (given Publisher Health already shows 2 series/2
issues) is being run — but I want the rebuild **wired to run after the multi-issue `--all` audit** so the
Registry can't go stale behind the dashboard. *Files:* `scout_delta_audit.py` / a trigger, `app.py`. *Risk:*
low. Sequence first (or fold into 2a's prep).

## 4. The comparability guard — where it actually lives

The **health** layer needs no guard: it aggregates categorical states (`healthy/attention/unknown`) via a
monotone rollup, never numbers. The guard belongs to the **metric** layer (2c/2d). The machinery already
exists — `scout_benchmark.build_projection` segments every aggregate by `geometry_comparability_key` /
`metadata_comparability_key`, so mixing methodologies is structurally prevented as long as we **never
average across comparability keys** and **series-vs-series compares like-methodology segments (or explicitly
marks the boundary)**. SXI-2c inherits this and I'll assert it under adversarial review, the same
dual-condition discipline we used for the metadata versions.

## 5. Proposed sequence (for your confirmation)

`2e (freshness) → 2a (issue picker) → 2b (title-group + cross-series) → 2c (scope serving + guard) → 2d
(compare + composite)`. Rationale: 2a is the biggest founder-value unblock and is low-risk; 2b closes §3;
2c/2d are the deeper analytical build and depend on the guard landing first. Each ships and deploys on its
own.

## 6. Open questions — for Johnny + Keystone

1. **Label:** render the level as **"Title Group"** (ratified `title_group_id`) or the founder-facing
   **"Universe"**? (Johnny flagged the founder reads it as Universe.) I'll use whichever you ratify; my
   default is *"Title Group"* with *"Universe"* as a secondary label if the founder prefers.
2. **Scope of this pass:** is the **composite/overall** view (2d) wanted in SXI-2, or should SXI-2 stop at
   per-series + series-vs-series and defer composite? (Composite is cheap since platform benchmark +
   publisher health already exist — but it's the one "new synthesis" surface.)
3. **`title_group_health` projection:** worth adding the rollup level (2b optional), or is a display-only
   title-group grouping enough for now?
4. **Priority / timing (Keystone):** is SXI-2 greenlit to start now (2a first), or held behind other work?
   Johnny's walkthrough is the field evidence — the founder hit §2 and §3 within five minutes.

## 7. What I need from the Publisher

**Nothing structural** — no contract change, no new emission. Only a confirmation that `title_group_id` is
stable and that `society_universe ▸ society_of_killers` / `i_ride_for_them`'s own title group are the correct
groupings to render. If a series ever moves title groups, that's a Registry-rebuild event Scout already
handles.

Awaiting your go (and answers to §6) before I start SXI-2a under the certified-first discipline. — Atlas
