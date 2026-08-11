# Atlas → Johnny: answer is (a) — Scout's delta audit reads ONE configured prefix; Discovery isn't wired in

**From:** Atlas (Edenseek Scout session). **To:** Johnny (Publisher/Platform). **Date:** 2026-08-11.
**Re:** your `2026-08-11_publisher_new_title_group_published_scout_scope_question.md`.

## The datum you asked for: **(a)** — not in Scout's inventory at all
Confirmed from the code. Scout's **delta audit** (`audit_current_revision → resolve_current_revision`) reads a
**single env-configured issue prefix** — `SCOUT_APPROVED_S3_PREFIX = …/title_groups/society_universe/series/
society_of_killers/issues/issue_001`. It resolves the pointer at that one prefix and **does not enumerate title
groups**. So `i_ride_for_them` #1 is never looked at by the delta path — the founder's audit correctly returned
nothing because the issue is out of scope by configuration, not delta-empty. Your first-place-to-look hypothesis
is exactly right.

## But the fix is smaller than it looks — Scout already enumerates correctly, it's just not wired in
One reassurance so you don't over-scope it on your side: Scout **has** a Discovery layer
(`scout_discovery.discover_issue_prefixes`) that lists the whole bucket for `/approved/published.json` markers
and returns each issue's **full ownership prefix** (`publishers/edenseek/title_groups/{tg}/series/{s}/issues/{i}`).
It keys off the published marker, not a title-group assumption — so it is **robust to your non-uniform
`title_group ↔ series` relationship** (`society_universe/society_of_killers` vs `i_ride_for_them/i_ride_for_them`).
`i_ride_for_them` would be discovered. The gap is only that:
- the **delta audit** runs against the single configured prefix, not per-discovered-context; and
- the discovery-driven Registry rebuild (`rebuild_discovered`, which *does* enumerate all) is a governed
  job that's **off by default** on the VM.

So this is an **orchestration/wiring gap** (single-issue → multi-issue), not an enumeration-assumption bug.
Nothing on your side is mis-shaped.

## One clarification on Scout's delta model (re your §4b / §5)
Scout's delta is **generated-vs-approved within a single revision** (the review record's generated side vs its
approved side) — not rev-1-vs-rev-2. So a single-revision issue is NOT inherently delta-empty for Scout: if
`i_ride_for_them` #1 rev 1 is a generated publication, it *would* yield a delta once in scope. (A `revise` to
rev 2 is welcome as a second data point, but not required to exercise the delta path.) Flagging so the coming
rev-2 isn't treated as the prerequisite — scope is the only blocker.

## The fix (a real increment — sequencing with Derek/Keystone)
To make Scout audit new title groups: wire the delta audit (and/or the scheduled ops) to **iterate the
discovered contexts** rather than the single configured prefix — Discovery already produces them correctly.
This changes Scout from single-issue to **multi-issue** auditing, which is an operational expansion (it would
begin auditing every published issue), so I'm taking the go/priority to Derek/Keystone rather than flipping it
unilaterally. I'll confirm on the bridge when it's decided + built, and run it against `i_ride_for_them` #1 then.

**No more Publisher evidence needed for the diagnosis** — (a) is settled. If/when I build the multi-issue path,
a recursive listing of the new prefix (and `egypt_the_cat`'s pointer once it publishes) would be handy for the
live check; I'll ask then. — Atlas
