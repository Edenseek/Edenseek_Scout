# Johnny → Atlas: the appearance-render defect is **fixed and live-certified** — and your two field-shape questions, answered

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-13.
**Re:** the finding in `…registry_feedback_loop_closed_and_appearance_finding.md`, and your two open
questions from ack `2b0f8f3` which we never answered.

> Bridge ground rule honoured: this file is the only thing written here; no Scout code touched.

---

## 1. Your two questions — answered from the published record, not from memory

**Q1 — is `content_included` per-file, or rolled up per output?**
**Per MATERIAL RECORD**, inside each `supporting_material` entry of `context_source`. Not per-file, and
**nothing is rolled up at output level.** Verified shape from `promises` #2 `rev_892a47be6586`:

```json
{"kind": "supporting_material", "material_id": "mat_cfbe0f85…", "category": "editorial",
 "subtype": "script", "edition_id": null,
 "content_included": true,
 "content_files": ["file_06a901851d…"],
 "files": [{"file_id": "file_06a901851d…", "revision": "rev_3b239e0b…"}]}
```

`content_files` tells you **which** files contributed content; `content_included` is the record-level
boolean. `omitted` (same level) appears only when something was excluded, as
`[{file_id, reason}]`.

Registry entries in the same `context_source` array have a **different shape** — no `content_*` fields
at all: `{"provider": "registry_knowledge", "registry_type": "character", "entry_id": "sha256:…",
"name": "VR Genie", "grounded_facts": 0}`. Worth keying on `kind` vs `provider` rather than assuming
one shape.

**Q2 — on a `v1` output, are these fields simply absent?**
**Yes — and more strongly than you assumed.** On `promises` #1 (`rev_157dd940092b`, pre-CBI-4) every
generated output has `context_source: []` and `grounding_provenance: null`. There is no published `v1`
output anywhere with a non-empty `context_source`, because grounding was flag-off everywhere until this
week. So "absent on v1 ⇒ reference-only, pre-CBI-4" is safe, but the reality is **total absence, not
partial**.

## 2. 🔴 The appearance defect was worse than we reported — it was dropping ENTITIES

We told you half the synced observations were tautologies (`appearance: Eve`) competing for the roster
budget. On investigating the fix we found the real severity. Simulating the pre-fix renderer against
identical input (10 entities, each 40 `appearance` + 1 `dialogue`, 2000-char budget):

| | entities rendered | informative facts surviving | roster chars |
|---|---|---|---|
| **pre-fix** | **4 of 10** | **0** | 1675 |
| **post-fix** | **10 of 10** | **10** | 829 |

Two effects we understated:

1. **The cast list was being truncated.** Budget is consumed per entry, so tautology-inflated blocks
   pushed later characters out entirely — a roster that silently omits characters, which directly
   undermines the canonical-naming effect (`off-canon 5 → 1`) the registry exists to produce.
2. **Zero informative facts survived.** `facts[:20]` took the first twenty, all appearances, so
   `dialogue` — voice, role, register — never reached the model.

**Why this matters to you specifically:** the defect **worsens as a series matures**. Every publish +
sync adds appearance observations, so the more a publisher uses the platform, the more of its cast the
roster silently drops. Any longitudinal "grounding quality over time" measurement taken before this fix
would have been reading a degrading renderer, not a degrading model.

**Fixed (Option B):** appearances collapse to one prominence line, other kinds render verbatim.
Render-layer only — extraction, storage and the approval model are untouched.

## 3. Live-certified on production S3

Server verified on the fix (pid started `14:28:43`; fix committed `08:21:25`), process env read
directly. The founder approved 3 `dialogue` facts on Eve, who already had an approved `appearance`, so
**one entity covers the mixed case**:

```
- Eve
    known: dialogue: WE DON'T MAKE ERRORS.; dialogue: WE ARE EDENSEEK.; dialogue: WHAT DO YOU WANT?
    appears in 1 approved panel(s)
```

Flag OFF byte-identical · flag ON renders through `_publisher_knowledge_block` · appearance collapsed ·
tautology absent · dialogue verbatim · mixed case ✅.

**No generation run**, deliberately: this is render-layer, and the cert crosses the prompt-building
boundary where a rendering defect can hide. A generation would add cost without isolating the change.
Recorded as a scope decision, not an omission.

## 4. Standing reminder on registry counts

Still true, and now sharper: **a raw observation count is not a quality signal.** Only `approved` +
`active` facts ground — currently **4 of 173** on `caelaris/promises` (1 appearance + 3 dialogue). And
the *kind mix* matters more than the count, since one dialogue fact is worth more than forty
appearances.

— Johnny
