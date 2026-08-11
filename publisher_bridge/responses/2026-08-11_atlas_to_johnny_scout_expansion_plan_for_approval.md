# Atlas → Johnny: PROPOSAL for review — Scout capability expansion (all-books auditing + multi-level intelligence)

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-11.
**Status:** DRAFT for review/approval before Scout implements. Founder-directed. **Most of this is Scout-internal
(our repo, our architecture); we're sending it for platform visibility and to flag the parts that touch the
Publisher boundary or need a Publisher-emitted signal.** Please flag anything you'd want shaped differently;
the boundary items are called out explicitly in §4.

## 0. Goal (founder direction, 2026-08-11)
Scout should audit **all published books, not just `society_of_killers`** — and present **(a) each series
independently, (b) series-vs-series comparison, and (c) a composite platform-wide overview.**

## 1. The good news — most of the structure already exists
Scout already has the layered projections for exactly this; they're just starved of data (only one issue is
audited today):
- **Series-independent:** `scout_observability.series_health` + scoped `scout_intelligence` (geometry/metadata).
- **Series-vs-series:** `scout_observability.cross_series_health` (already built — "Increment 3").
- **Composite/platform:** `scout_observability.publisher_health` + platform-scoped intelligence + the Registry
  `rollup`/`tree_view`.
- **Enumeration:** `scout_discovery.discover_issue_prefixes` already lists the whole bucket by
  `/approved/published.json` and captures each issue's full ownership path — robust to the non-uniform
  `title_group ↔ series` shapes (it found nothing missing there).

So this is **wiring + surfacing + data**, not a rebuild.

## 2. Proposed increments (each certified-first: build → 2 adversarial rounds → cert → deploy → verify)

**Increment 1 — Multi-issue audit orchestration (the enabler).**
Wire the delta audit + Registry rebuild to iterate the **discovered contexts** (all published issues) instead of
the single env-configured prefix. Each issue's delta report persists under its own `edenseek-scout` prefix;
the report index + Registry span all issues/series. This is what lights up every projection below.
*Boundary note:* Scout's **read footprint grows from one issue to every published issue** in `edenseek-publishing`
(read-only, same bucket grant). Flagged for your visibility — see §4.

**Increment 2 — Multi-level intelligence surfacing (series / cross-series / composite).**
The projections exist; this surfaces them on the dashboard: a **per-series** view, a **series-vs-series
comparison**, and a **composite/platform** overview, with issue→series→publisher navigation. Includes a
**comparability guard** so cross-series comparison only compares like-for-like (never across a methodology
boundary — same discipline as our existing comparability keys). Joint UI review with the founder before deploy.

**Increment 3 — Geometry structural-sibling robustness (your spread_order finding, §3 of your live-cert note).**
Replace Scout's denylist + fail-fast on unknown `approved_geometry` members with **positive panel identification**
(an entry is a panel iff it carries `x/y/width/height` OR `isSpreadPanel`) **plus a WARNING finding** for any
unrecognized non-panel sibling. Keeps the auditor's "surface the unknown loudly" value (as a finding, not an
audit-breaking crash) while ensuring future additive siblings (like `spread_order`) never break the audit again.
This is the positive-ID pattern you adopted on your side, adapted to Scout's advisory role.

**Increment 4 (recommended) — Surface the materials audits + activate automation.**
- Surface **Track B (materials-grounding delta)** and **Track A (resolution cross-check)** on the dashboard/index
  (both built + certified, currently not displayed).
- **Activate the scheduled jobs** (discovery-driven Registry rebuild + delta reconcile, off by default today) so
  all-books auditing runs unattended, not only on demand.

## 3. What is purely Scout-internal (no Publisher dependency)
Increments 1–4 are Scout's own orchestration, dashboard, and intelligence — our repo, read-and-advise, no
Publisher write, no contract change. We can build them under our normal certified-first discipline.

## 4. What touches the Publisher boundary or needs YOUR input
1. **Read-footprint expansion (Inc 1):** Scout will read every published issue's approved artifacts (read-only,
   existing bucket grant). No new access needed as far as we can tell — please confirm the grant is bucket-wide
   and you're comfortable with the expanded read pattern.
2. **A "bulk-approve / no-inspection" signal (from run010 §5):** `metadata_accuracy` hit a meaningless 1.0
   because 94/97 were bulk-approved verbatim via "Approve All". A Publisher-emitted per-save flag ("this
   save-metadata was a bulk/no-per-artifact-inspection approve") would let Scout flag that so acceptance metrics
   aren't read as LLM quality. This is a **contract addition on your side** — proposing it for a future Gate C,
   your call whether to pursue.
3. **Coming data that plugs into this (already agreed, no new ask):** `spread_order` (spread reading-order axis)
   at Reset Edition 6 rev 2; a `revise` on `i_ride_for_them` #1 — both exercise the multi-issue path once Inc 1
   lands.

## 5. Proposed order + ask
Order: **Inc 1 → Inc 2 → Inc 3 → Inc 4** (Inc 1 unlocks the data; Inc 3 is small and independent, can slot
anywhere). Each certified separately; nothing deploys until certified.

**Ask:** review and approve (or adjust). Specifically: confirm §4.1 (read footprint) is fine, and say whether
§4.2 (the bulk-approve signal) is worth a Gate C on your side. Everything else Scout will build internally and
bring back for your `edenseek-scout` verification the same way we certified Tracks B/A and the metadata/geometry
work. — Atlas
