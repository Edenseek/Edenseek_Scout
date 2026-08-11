# Johnny → Atlas: ADVANCE NOTICE — `approved_geometry` will gain a third structural sibling (`spread_order`)

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-11.
**Re:** Publisher Gate C **approved today, NOT yet implemented**. Sent at approval rather than at
implementation, deliberately — see §5. **Action likely needed on your side before it ships.**

Self-contained as always — Atlas has no read access to the Publisher repo.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. What is changing

`approved_geometry` (and `saved_geometry`) will gain **one additive key**:

```
spread_order: { "12-13": ["12::NEW::2", "12::NEW::1", "12::NEW::3"], … }
```

- keyed by the spread canvas's **page range** (founder decision, 2026-08-11);
- value is the publisher's chosen **reading order** for that spread's panels;
- **additive** — nothing is removed, renamed, or restructured.

**Nothing has shipped yet.** No published edition carries this key today, and none will until the
increment is built and live-certified.

## 2. Why — and the part that concerns you

Today, **page** panels store their reading order in `panel_order`, while **spread** panels have theirs
**derived geometrically** at read time (row-major over spread-space bounds). So a publisher cannot
correct a spread's reading order at all: there is nowhere to record the intent. That is currently
blocking real editorial work — on `society_of_killers` #1, five of the nineteen multi-panel pages are
spread canvases carrying 34 spread panels, and those are precisely the ones whose order is wrong.

**The consequence for you is the interesting half.** Because spread order is *derived* rather than
*recorded*, **you cannot audit it today** — there is no artifact to compare against, so a wrong spread
reading path is undetectable by construction. Once `spread_order` exists, spread reading order becomes
**auditable for the first time**. That is a new axis available to you, not a defect being papered over.

## 3. What we think you need to do — **F1 precedent**

`spread_order` is a **non-artifact structural sibling**, exactly like `panel_order` and
`spread_artifacts`. Your readiness/comparison logic already has to exclude those two from
artifact-level iteration — that was **fix F1** (`06a4de1`, "readiness excludes geometry structural
siblings"). **A third sibling needs the same treatment.**

If your code enumerates `approved_geometry` entries and assumes each is a panel, an unhandled
`spread_order` key would look like a malformed artifact. We would rather you hear that now than
diagnose it from a delta report later.

## 4. What is NOT changing

- No panel identity, geometry, `page_range`, `coordinate_space`, `stage_geometry` or crop changes.
- **No `artifact_geometry_hash` changes.** Reading order is a sequence over panels, not a property of
  any panel's bounds — confirmed empirically on 2026-08-11 when a page-order change left all 100 of
  `i_ride_for_them` #1's artifact geometry hashes byte-identical. **Reordering stales nothing.**
- No change to spread detection, spread registration, or canvas assembly.
- No metadata schema change (`v2` field contract untouched).
- Existing editions resolve exactly as they do today — absence of the key means the current geometric
  derivation, so there is no migration and no silent reinterpretation of anything already published.

## 5. Why you are hearing this now

The founder chose to notify at **Gate C approval** rather than at implementation, for two reasons:
F1 showed the readiness check must be updated *before* a new sibling reaches a published edition, and
you work asynchronously — scoping this when the design is settled beats discovering it in a delta.

**No reply strictly required.** Two things would genuinely help:
1. **Confirm the F1-style exclusion covers a third sibling** — or tell us it needs work on your side,
   and roughly how much, so we can sequence the live cert accordingly.
2. **Say whether spread reading order is worth an audit axis to you** once it exists. If it is, we can
   make sure what we emit is shaped for that rather than only for the reader.

## 6. Unchanged since the last bridge file

- **No new published edition** — still `rev_5e962c83…` (Reset Edition 6 rev 1, your `run000010`).
- Reader v2 Phases **1A and 1B are now live-certified** (founder-signed 2026-08-11); Phase 2's four
  additive tools are partially certified — three pass, and Panel Order was defective and is now fixed
  for page scope, which is what led here.
- **Track A** resolved-graph live cert remains parked. Phase 1 is not closed and V1 is not retired.
- The 124 generated metadata outputs on `egypt_the_cat` #1 and `i_ride_for_them` #1 remain unreviewed
  and unpublished, so still outside your read scope.
