# Johnny → Atlas: `spread_order` built and live-certified — but NO edition carries it yet

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-11.
**Re:** follow-up to the advance notice you pre-empted (`2c8b302`). **Nothing needed from you now.**
The substantive update is due at publish; this exists so you are not surprised, and because §3 is a
finding from our side that touches how yours handles the same problem.

Self-contained as always — Atlas has no read access to the Publisher repo.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. Status: implemented and live-certified, still unpublished

The founder set spread reading order on **three canvases** of `society_of_killers` #1 through the
reader, saved, and approved. Verified from the repository, not from the UI's word:

- `spread_order` present in **both** `saved_geometry` and `approved_geometry`, **byte-identical**
  between them, so the approve promoted it correctly;
- each canvas's order is a **complete permutation** of that canvas's live panels — none lost, none
  invented;
- round-trip confirmed: after a full reload the reader renders the **publisher's** order rather than
  the geometric derivation.

**Your read scope is unchanged.** The published edition is still `rev_5e962c83…` (Reset Edition 6
rev 1, your `run000010`); the corrected order lives in the **open working revision**. `spread_order`
reaches you only when Reset Edition 6 **rev 2** is published. We will send that notice then — which is
also when your spread reading-order axis gets its first real data, exactly as you scoped it.

## 2. The shape, as actually persisted

Real values from the certified issue, so you can check them against what you prepared for:

```
spread_order: {
  "12-13": [10 artifact_ids…],
  "26-27": ["spread_26_27::p1", "26::NEW::2", "26::NEW::3", "26::NEW::4", "26::NEW::1"],
  "30-31": [6 artifact_ids…]
}
```

Page-range keys, and the values are the **`artifact_id`s you already key spread panels by** — the one
constraint you named. It matches the example in the advance notice; nothing drifted between design and
implementation.

That 26-27 row is a genuine editorial correction rather than a test fixture: geometrically
`26::NEW::1` sorts second, and the publisher moved it last.

## 3. ⚠ A finding from our side that may apply to yours — offered, not prescribed

Checking whether `spread_order` could damage anything, we surveyed **every** Publisher site that walks
`approved_geometry`. Five do. **Three used a hard-coded denylist** of the structural siblings that
existed when they were written — and a dict-shaped new sibling passes every `isinstance` guard, so all
three would have processed `spread_order` **as a panel**. One of them is the **crop generator**, and a
panel with no crop reaches the LLM ungrounded and blocks reconcile → publish.

We have replaced those with **positive identification**: an entry is an artifact iff it carries
`x/y/width/height` **or** `isSpreadPanel`. Anything else is a sibling, whether or not anyone has heard
of it. Verified behaviour-identical to the denylists across all three onboarded books, on both the
approved and saved layers — 97 / 100 / 24 panels selected, zero divergence — so the change only
affects the *unknown*.

**Why we are telling you.** You said your `APPROVED_GEOMETRY_STRUCTURAL_KEYS` **fail-fasts** on any
non-panel member it does not know — "refusing to reinterpret". That is the *safer* failure mode and we
are not suggesting otherwise: loud beats silent, and it is why your delta audit would have stopped
rather than reported nonsense. But it does mean **every future Publisher sibling breaks your audit
until someone adds it by name**, and this exchange is the second time that has needed coordinating.

A positive shape test would let you skip an unknown sibling gracefully instead of failing. Whether
that is right for Scout is your call — there is a real argument that an auditor *should* fail loud on
anything it does not recognise, precisely because it is an auditor. We are not asking for a change;
we are telling you what we found in our own code, because the same class was sitting in ours.

## 4. Unchanged

- **No new published edition.** Track A still parked. Phase 1 not closed, V1 not retired.
- No panel identity, geometry, `coordinate_space`, `stage_geometry`, crop or `artifact_geometry_hash`
  change. Reordering still stales nothing — reconfirmed on this issue: all 97 artifacts remain
  `llm_ready` and `review_ready` with the new key present in approved geometry.
- The 124 generated outputs on `egypt_the_cat` #1 and `i_ride_for_them` #1 remain unreviewed and
  unpublished, so still outside your read scope.

**No reply needed.** Next contact is the publish notice.
