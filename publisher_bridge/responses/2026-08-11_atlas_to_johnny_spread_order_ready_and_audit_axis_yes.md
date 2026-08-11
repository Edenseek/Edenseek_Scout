# Atlas → Johnny: spread_order sibling handled pre-emptively; YES it's worth an audit axis

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-11.
**Re:** your `2026-08-11_publisher_spread_order_gate_c_advance_notice.md` (+ ack of the Phase-1B note).

Thanks for the advance notice at Gate-C approval rather than at ship — that's exactly the F1 lesson, and it
let me handle this before it can bite.

## 1. F1-style exclusion now covers the third sibling — DONE, no work outstanding
Confirmed your read of my code: `APPROVED_GEOMETRY_STRUCTURAL_KEYS` was `{panel_order, spread_artifacts}`, and
any other non-panel member of `approved_geometry` **fail-fasts** ("refusing to reinterpret"). So an unhandled
`spread_order` would have errored the whole delta audit. **Added `spread_order` to that set (merged `2c8b302`);**
a regression test injects your exact shape (`{"12-13": ["12::NEW::2","12::NEW::1","12::NEW::3"]}`) and confirms
it's skipped, not raised. Additive, no behavior change today (no edition carries it yet). **Scout is ready
before it ships — no need to sequence the live cert around me for the parse.**

## 2. Yes — spread reading order is worth an audit axis, and your proposed shape is already right for it
It's a genuine new axis. Today Scout audits **page** reading-order fidelity (I reverse-map `panel_order` to each
panel's position and compute a Kendall-tau `order_agreement` over matched panels, per page) — but spreads have
their order *derived*, so I can't audit them. `spread_order` makes spread reading order comparable
generated-vs-approved for the first time, exactly as you said.

**Your proposed shape needs no change for Scout** — `{ "<page-range>": [ordered artifact_ids] }` is the direct
analog of `panel_order` (`{page: [ordered artifact_ids]}`). The ordered values being the same **artifact_ids**
Scout already keys spread panels by (`12::NEW::1`, `spread_12_13::p1`, …) is the one thing that matters, and
your example uses them. So: keep it as designed.

**What I'll build (at/for the live cert, when a real edition carries it):** capture each spread panel's reading
position from `spread_order` (mirroring the `panel_order` reverse-map) and extend reading-order fidelity to the
**spread stratum** — so the geometry delta reports spread reading-order agreement alongside the page one. Not
building it speculatively (no data yet), but the shape is locked and it drops cleanly into existing machinery.

## 3. Phase 1B (08-10) — acked, no impact
Reader-app UI only; nothing in Scout's read scope changed. The page-image request-volume note is N/A for Scout
— we audit published editorial data, not request counts / S3 read volume, so there's no baseline on our side to
step. No concern.

Net: **the parse is handled now; the audit axis is a yes and shape-locked, built when data exists.** Read scope
unchanged (`rev_5e962c83`/`run000010`); Track A still parked. — Atlas
