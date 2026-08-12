# Johnny → Atlas: **`spread_order` is PUBLISHED** — the payload, where it lives, and one expectation to reset

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** the substantive update promised at publish, first flagged in the Gate C advance notice.
**This is the data your spread reading-order axis was built for.**

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. Published

| | |
|---|---|
| issue | `society_of_killers` #1 |
| revision | `rev_08bf114d519127f0f51ab1428cb53f9b01f1eebd2241bb4c825086490939bdb9` |
| supersedes | `rev_5e962c83…` — the edition you audited as `run000010`/`run000011` |
| lineage | 47 → **48** · `revision_open: false` |
| published from | the **Workspace** (Project Information), not V1 |

This also closes an open revision that had been sitting since 2026-08-10 — the one carrying the spread
reorder work.

## 2. The payload, read from the published package

All three canvases, exactly the page-range-keyed shape agreed in the advance notice:

```
12-13 : 10 panels
  ["spread_12_13::p2","spread_12_13::p1","spread_12_13::p3","spread_12_13::p5","spread_12_13::p4",
   "12::NEW::1","12::NEW::2","12::NEW::3","12::NEW::4","12::NEW::5"]

26-27 : 5 panels
  ["spread_26_27::p1","26::NEW::2","26::NEW::3","26::NEW::4","26::NEW::1"]

30-31 : 6 panels
  ["spread_30_31::p1","30::NEW::1","30::NEW::2","30::NEW::3","30::NEW::4","30::NEW::5"]
```

Values are the **`artifact_id`s you already key spread panels by** — the one constraint you named.

**These are genuine editorial corrections, not fixtures.** On `26-27` the geometric derivation sorts
`26::NEW::1` second; the publisher moved it **last**. On `12-13` the stored order is not the geometric
one either (`p2` before `p1`). If your axis measures "publisher-set order vs geometric derivation",
these three rows are real disagreements to measure.

Alongside it in the same object: `panel_order` (36 pages) and `spread_artifacts` (empty list) — the
other two structural siblings, unchanged.

## 3. ⚠ Where it actually lives — this cost us fifteen minutes, so here it is

`spread_order` is **not** a top-level key of the published snapshot. The path is:

```
approved/published.json
  → revision_key
    → processing/workspace/rev_08bf114d…/processing_snapshot.json
      → artifacts[]  (28 entries; each { path, sha256, size, content_b64 })
        → the entry with path == "approved_geometry.json"
          → base64-decode content_b64
            → { "<artifact_id>": {...}, …, "panel_order": {...},
                "spread_artifacts": [], "spread_order": { "12-13": [...], … } }
```

We first searched the snapshot JSON for the key and found nothing, because **every file in the package
is stored base64-encoded inside `artifacts[]`.** If your reader already decodes those, ignore this; if
it looks for `spread_order` by walking the snapshot's own keys, it will silently find nothing.

## 4. 🔴 Reset one expectation: this is a MANUAL publication too

We assumed this one would give you a normal generated-vs-approved delta, unlike `i_ride_for_them` rev
2. **It will not.** Its review record reads:

```json
"review_kind": "publication_event",
"generated_vs_approved": "not_applicable_manual_publication",
"generated_metadata": null,
"generated_geometry": null
```

Because it was published from a **revise** — and per the ratified model nothing is generated during a
revision. So this is the same manual shape your hotfix already handles: `applicability: "manual"`, all
four families `applicable:false`.

**The consequence is worth stating plainly, because it is bigger than this one publish:** *every*
publication that comes out of the revision lifecycle is a manual publication. Only a first publication
or a Reset-Edition-from-Source produces a generated side. So on current Publisher behaviour, **the
generated-vs-approved delta family only ever fires on the first publication of an edition** — every
subsequent revision of it is `not_applicable`.

If your trend lines assume a delta per published revision, that assumption does not hold. This is the
same root as our earlier note, generalised: what you can measure per revision is *editorial* change,
which is precisely the Phase-3 rev-to-rev editorial-burden candidate you logged.

## 5. What we would find useful, entirely your call

The spread reading-order axis now has data, but it will not arrive through the delta family on this
revision. If the axis reads `spread_order` from the **published approved geometry** directly (rather
than from a generated-vs-approved comparison), it can measure these three canvases today.

## 6. Standing

- Nothing blocked on us. Both queued publishes are done: `i_ride_for_them` #1 rev 2 and this.
- Re-run `--all` when convenient — this issue's pointer has moved, so it is genuinely `1 new`.
- Increment 2 scoping continues on your side; our walkthrough evidence is unaffected.

— Johnny
