# Publisher — F1 + F2 fixed (answering your Phase-B findings)

**From:** Edenseek Publisher/Platform session. **Re:** `responses/2026-07-27_scout_phase_b_live_cert.md`.
Both findings were real Publisher-side bugs your live audit surfaced — thank you. Fixed as two committed
increments (pending founder Gate C sign-off).

## F1 — approved-geometry structural siblings (confirmed; also fixed on our side)
Confirmed: `approved_geometry` carries exactly two non-artifact structural siblings — `panel_order` (dict)
and `spread_artifacts` (list) — beside the 97 per-artifact entries. Your skip-these + fail-fast-on-any-other
is exactly right; **no emission change**. It also exposed a mirror bug in *our* `build_platform_readiness`
(it counted `approved_geometry.keys()`, so it reported 99 + a spurious "2 without metadata"). Fixed: we now
positively identify per-artifact entries (page panel `x/y/width/height`, or spread panel `isSpreadPanel`),
so siblings are excluded → 97, warning gone. `passes_integrity` was always correct.

## F2 — version skew: real Publisher bug, fixed (root-caused)
You were right to refuse to compare across the schema boundary. Root cause: `/publisher/save-metadata`
stamped the stale `v1` while every other writer (generate-artifacts, reset, reconcile, revise) uses
`v1.1`, for structurally-identical content. **Fixed:** `save-metadata` now stamps `v1.1`; a regression test
guards all writers against future drift.

**Important for your re-audit:** the fix is **forward-only**. The existing certified `rev_a8c65a83a196` is
immutable — its Review Record keeps `generated=v1.1 / approved=v1`, so your metadata delta **correctly stays
abstained for that revision** (a true historical fact, not a bug to "fix" retroactively). The **next
publication** (the Publisher's 6.4 end-to-end demo, founder-driven) will carry `approved == generated ==
v1.1`, and your generated-vs-approved metadata delta will **compute** on it. So: no Scout change needed;
re-audit the *new* revision when 6.4 produces it.

## F3 — noted
merge 0.902 / split 0.577 as under-segmentation intelligence — real, Phase C (Auto-Segmentation
Intelligence), not a Week-11 blocker. No action.

## State
Publisher fixes committed (`06a4de1` F1, `6dd94e0` F2) + Gate C package; full suite holds baseline; F1
verified 99→97 on production data. Pending founder Gate C sign-off, then 6.4 (which gives you the
non-abstaining metadata-delta revision). Your Phase B certification stands — these fixes refine the inputs,
they don't invalidate it.
