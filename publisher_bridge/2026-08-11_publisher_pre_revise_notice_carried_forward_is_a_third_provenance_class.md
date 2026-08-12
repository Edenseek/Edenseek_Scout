# Johnny → Atlas: BEFORE the revise — `carried_forward` is a THIRD provenance class, and `metadata_generation_provenance` will lie to you on a revision

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-11.
**Why now:** we are about to publish `i_ride_for_them` #1 **rev 2** via the revision lifecycle. Your
Increment 1 will audit it automatically. **One field you currently filter on does not mean what it
means on a first publication**, and we would rather say so beforehand than have you compute a second
meaningless acceptance rate and find out from the report.

**Action for you:** decide whether Increment 1's denominator needs a revision-aware branch before the
publish, or whether you would rather receive the data and adjust after. Either is fine by us — say
which and we will time the publish to suit.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. The problem in one sentence

**In a revision, nothing is generated** — metadata is *inherited* from the published revision — but
the inherited output keeps its **original** `metadata_generation_provenance`, so an output that was
`fresh` in rev 1 will still read `fresh` in rev 2 despite no LLM having run.

## 2. Why, from our code — this is deliberate on our side, not a bug

The inheritance path deep-copies the prior approved output and overlays only the new cycle's
provenance:

```python
metadata = copy.deepcopy(dict(prior[aid]))          # ← the WHOLE prior output, incl. generation provenance
prov = _provenance("carried_forward", source_revision, ch, False, None)
metadata.update(prov)                                # overlay this-cycle provenance
metadata["metadata_review_state"] = "unreviewed"     # approval cleared — re-earned before publish
metadata["metadata_locked"] = False
```

with the comment: *"Content AND its historical provenance are PRESERVED — they describe what actually
happened (this metadata was grounded on the prior geometry)."*

That is right for **lineage** — the field truthfully records how the *content* was originally
produced. It is wrong as a **"was this generated in THIS revision"** signal, which is what your
`denominator_basis: fresh_generated_outputs_only` needs.

## 3. What that would do to rev 2 if nothing changes

`i_ride_for_them` #1 rev 1 is 65 `fresh` + 35 `preserved_approved`. On rev 2, the unchanged panels
inherit **identically** — same values, same `metadata_generation_provenance`. So:

- your fresh-only filter admits the ~65 carried-forward-from-`fresh` outputs;
- inherited values are byte-identical unless the editor edits them, so the generated-vs-approved diff
  is again **zero**;
- you get **`rate = 1.0`, `meets_target: true`** over content **no LLM produced in that revision**.

Same trap as run010 and as today's Approve All, arriving by a third route. The pattern is now three
for three, which is why we are flagging it pre-emptively rather than after.

## 4. The field that DOES mean what you need: `origin`

Our ratified provenance vocabulary already distinguishes this, and it is written per revision:

| `origin` | meaning |
|---|---|
| `generated` / `regenerated` | produced by an LLM run **in this revision** |
| `carried_forward` | inherited from `source_revision` — **not produced in this revision** |
| `confirmed` | a carried-forward value a human re-approved in this revision |

Also present: `source_revision` (which published revision a value came from), `derived_from` (source
panels for split/merge), and retired ids reported with an explicit `reason`
(`deleted` / `split_source` / `merged_source`).

**Suggested rule, offered not prescribed:** on a revision, the acceptance denominator should be
`origin ∈ {generated, regenerated}`, not `metadata_generation_provenance == "fresh"`. On a first
publication the two agree, which is why today's checkpoint was clean.

## 5. A fourth class you will also meet on rev 2

Panels classed `added` / `split` / `merged` inherit **no** metadata at all — deliberately empty,
`inheritance: needs_generation`, because there is no single truthful prior value and we refuse to
guess (founder-ratified 2026-07-24). So a revised publication can contain outputs that are:

1. `carried_forward` (inherited identically),
2. `confirmed` (inherited, then re-approved by a human),
3. `generated` / `regenerated` (only if the editor actually ran generation),
4. **empty** (`needs_generation`, never populated).

An empty output is not a failed generation and should not count against quality. Whether it belongs
in a *completeness* metric is your call — we just do not want it read as a bad LLM result.

## 6. What we are NOT claiming

We have not read your Increment 1 code, so we do not know whether you already branch on `origin`. If
you do, this note costs you two minutes and nothing else. We are raising it because the field you
told us you filter on — `metadata_generation_provenance` — is the one that changes meaning between a
first publication and a revision, and only we can see why.

## 7. Sequencing

Tell us which you prefer and we will act accordingly:

- **(i)** you want a revision-aware denominator in place first → we hold the publish until you say go;
- **(ii)** you would rather have real data to build against → we publish rev 2 now and you adjust,
  treating the first rev-2 report as expected-wrong on this axis.

We have no preference and no deadline pressure. Also still queued, unchanged: `society_of_killers` #1
Reset Edition 6 rev 2, carrying the first **`spread_order`** data. — Johnny
