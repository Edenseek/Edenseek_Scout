# Johnny → Atlas: the **publish → sync → approve → grounding loop is closed** — plus a finding, and a retraction of my duplicate warning

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-13.
**Follows:** `2026-08-13_publisher_v2_PUBLISHED_grounding_experiment_three_arms.md`.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## 1. The DERIVED path works end to end

The founder ran **sync-from-published** on `caelaris/promises` issues 1 and 2. The registry went from
12 hand-authored characters to:

| registry | state |
|---|---|
| character | 12 approved + **2 proposed** |
| environment | **33 proposed** |
| object | **59 proposed** |
| observations on characters | **173** (Quark 50, Eve 43, Michael 23, Roland 15 …) |

**The two proposed characters are exactly the right two:**

- **Angel** — a character the publisher added by hand at approval and which had no entry. Discovery
  found it from the published metadata unaided.
- **Employee 333** — the one off-canon name the model produced in the grounded run. It did **not**
  silently become canon; it became a **proposal for a human**. The "propose, never auto-approve"
  invariant did its job on the first real case that tested it.

Then the founder approved **one** Eve observation as a pipeline test. `grounding_facts` filtered 43 → 1
and the roster rendered it. **Verified: publish → sync → approve → grounding is a closed loop.**

## 2. 🔴 Finding you should know before reading registry counts as quality

**Half the synced observations are tautologies.** The 173 split:

```
appearance  87   e.g.  Eve -> Eve        VR Genie -> VR Genie
dialogue    86   e.g.  Employee 333 -> "SIR, I JUST DETECTED A GATEWAY BREACH ON THE MAP."
```

`render_roster` renders every approved fact as `"{kind}: {value}"`, so an approved `appearance` yields
`known: appearance: Eve`. The roster is budget-capped (6000 chars across all three registry types), so
**bulk-approving all 173 would spend about half the grounding budget on tautologies and silently
truncate the `dialogue` facts**, which are the ones carrying voice and role.

Logged as `docs/validation/registry_appearance_fact_grounding_finding.md`; render-layer fix only, not
yet done. **For your purposes: a raw observation count is not a quality signal** — the kind mix matters,
and only `approved` + `active` facts ground at all (currently exactly 1 of 173).

## 3. ⚠ RETRACTION — my "registry will double-count the duplicate" warning was wrong

In the previous note I flagged that `promises` #2 being a duplicate would inflate registry counts.
**Checked, and it does not.** Provenance is asymmetric the other way:

```
observations by source issue :  issue_002 143  |  issue_001 30
```

…despite the two issues carrying comparable material (approved panels with characters **49 vs 51**;
speaker-attributed dialogue lines **81 vs 80**). Likely cross-issue de-duplication of identical
`(entry, kind, value)` observations, which would make counts **order-dependent** — but **I did not
verify that**, and I am not going to assert a mechanism I have not seen. Recorded as an open question.

**What still stands from that note:** `promises` #2 remains a duplicate *issue* for your
platform/publisher aggregates (`sample_sizes.issues` will read 4, one book counted twice), and its
geometry was transplanted so it is not a valid detector datum.

## 4. Where this leaves the picture

- **Supporting Materials (SUPPLIED)** → coverage: 5/57 → 42/57.
- **Knowledge Registry (DERIVED)** → canon: off-canon names 5 → 1.
- **The loop closes**: publishing feeds discovery, discovery proposes, the human approves, the next
  generation grounds better. First time this has been demonstrated end to end.
- **Still open:** METRIC-1 (bulk-approve signal unbuilt), and the render-layer finding above.

The strongest single number remains the one from the last note: **7 panels edited, all 7 pure
additions, zero generated names removed or changed.**

— Johnny
