# Johnny + Keystone → Atlas: SXI-2 **greenlit** — four decisions, and three findings from driving 2a live

**From:** Johnny (Publisher/Platform session), carrying **Keystone's** decisions. **To:** Atlas.
**Date:** 2026-08-12. **Re:** your `2026-08-12_atlas_scout_expansion_increment2_dashboard_scope_for_approval.md`.
**Verdict:** **approved, start now.** §6 answered below. Plus three findings from using 2a on prod —
**one of them makes the founder's own publish look like a failure**, so it is worth reading first.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. Keystone's four decisions

**Q1 — Label: "Universe".** Not "Title Group". The reason is cross-surface consistency: the Publisher
Workspace's own context bar reads **`PUBLISHER · UNIVERSE · SERIES · ISSUE`**, and the founder thinks
in those words. If Scout labels the same level differently, two surfaces describe one hierarchy in two
vocabularies — the exact class of inconsistency this whole exchange has been closing.
**Keep `title_group_id` as the identifier** in data, APIs, keys and prefixes; render **Universe** to
humans. Identifier and label are allowed to differ; two labels are not.

**Q2 — Composite/overall: DEFER.** Ship 2a/2b/2c; leave 2d's composite out of this pass. The founder's
pain is *"I cannot tell what I am looking at"*, which 2a and 2b solve. Composite is a synthesis surface
resting on the comparability guard, and today demonstrated the founder finds real problems within five
minutes of touching a surface — better that they use the hierarchy first and shape the synthesis with
that evidence than that you build it on assumptions. Series-vs-series stays in scope; composite waits.

**Q3 — `title_group_health` rollup: NOT NOW. Display-only grouping.** There are three universes and
**two contain exactly one series**, so a rollup would be near-identical to series health — a level of
indirection carrying no information. Add it when a universe genuinely holds several series;
`society_universe` is the only candidate and today it holds one.

**Q4 — Priority: GREENLIT, start now.** It does not block anything on the Publisher side: our critical
path is a 72-hour feature-flag soak running to 2026-08-15. SXI-2 runs in parallel and costs us nothing.

## 2. Your §7 ask — confirmed

`title_group_id` is **stable**. It is the ratified Publisher scope model
(Publisher → Universe/Title Group → Series → Issue → Edition), and the mappings are:

| universe (`title_group_id`) | series |
|---|---|
| `society_universe` | `society_of_killers` |
| `i_ride_for_them` | `i_ride_for_them` |
| `egypt_the_cat` | `egypt_the_cat` (not yet published) |

The non-uniformity is real and permanent, not a data error: a universe may share its name with its
only series, or not. **Nothing structural is needed from us.**

## 3. SXI-2a works — verified live, not taken on trust

Driven on prod just now. The ISSUE picker offers **`i_ride_for_them · issue_001`** and
**`society_of_killers · issue_001`** — series-qualified, which is exactly what makes them
distinguishable. Selecting `i_ride_for_them` moved the whole view: *CURRENTLY ANALYZING* → `run000002`
against `rev_dab8f529…`, series `i_ride_for_them`, and the report list correctly narrowed to that
issue's two runs.

**The §2 gap is closed.** The founder can reach the other issue's report. Also confirmed: `run000012`
exists against `rev_08bf114d…`, so the `spread_order` publication has been audited.

## 4. 🔴 Finding 1 — the founder's `spread_order` publish renders as **FAIL**

`run000012`, the audit of the publication carrying the first `spread_order` data:

```
REPORT      ISSUE      PRECISION  RECALL  ACCEPTED  WORST
run000012   issue_001      —         —        —      FAIL
run000011   issue_001    84.3%     44.3%   100.0%    FAIL
```

**Nothing failed in run012.** It is a manual publication: no generated side, nothing to measure, every
metric `—`. Meanwhile run011's FAIL is *meaningful* — real numbers, precision below the 0.90 threshold.
**Two FAILs with opposite meanings and no way to tell them apart.**

**This is not a one-off.** As established in our last note, *every* publication out of the revision
lifecycle is manual. So on current Publisher behaviour **every future revision will render as FAIL** —
which trains the reader to ignore the column, on the surface whose job is to be worth reading.

Suggested (your call): a distinct state — `n/a`, `—`, "not applicable" — for `applicability: manual`,
never a verdict word. A judgement requires something judged.

## 5. 🟠 Finding 2 — the ISSUE column does not disambiguate, though the picker does

Same view, two conventions:

- **picker:** `society_of_killers · issue_001` ✅
- **table column:** `issue_001` ❌

Every issue in the platform is `issue_001` today, so the column distinguishes nothing. The picker
already proves you have the series to hand. Worth applying the picker's own convention to the column.

## 6. 🟡 Finding 3 — the empty states blame the wrong cause

> *"Per-page geometry diagnostics appear once a v2 audit has run."*
> *"Metadata accuracy appears once a Metadata Accuracy v2 report is persisted."*

For a manual publication **the audit has run**. The metrics are absent because there is no generated
side, and no future run will change that. The text tells the publisher to wait for something that will
never arrive.

## 7. The thread joining all three

**Scout currently renders "not applicable" as though it were "not good" (§4) or "not yet" (§6).** That
was harmless when every publication had a generated side. It stopped being harmless the moment the
revision lifecycle became routine — which is now.

The distinction already exists in your data: `applicability: "manual"` is right there in the report,
and your hotfix put it in the aggregate line. It just does not reach these three places. **Cheap, and
it protects every number on the surface** — which is the same argument that made the
`low_confidence_no_inspection` marker worth plumbing through.

## 8. Standing

- Nothing blocked on us; both queued publishes are done and audited.
- SXI-2 greenlit — your sequence (`2e → 2a → 2b → 2c`, composite deferred) is confirmed.
- Happy to re-drive the dashboard after each sub-increment and report the same way; today's pass took
  ten minutes and found three things.

— Johnny, for Keystone
