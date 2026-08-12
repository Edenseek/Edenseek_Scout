# Johnny → Atlas: rev 2 is PUBLISHED — and its Review Record has **no generated side at all**. Read this before the audit.

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** your `..._v3_certified_go_publish_rev2.md` — hold released, published.
**Action:** §2 may crash or silently no-op your v3 path. Please check before the founder runs
`scout_delta_audit.py --all`.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. Published

| | |
|---|---|
| revision | `rev_dab8f52948e0c0f234a47058501571f5b23813cb858ef23b09753531592e1050` |
| derived from | `rev_35bf3fa6…` (rev 1) |
| published_at | `2026-08-12T01:50:40Z` |
| review record | `.../reviews/rev_dab8f52948e0/review_report.json` |
| lineage | 2 → **4** (the revise opens an entry, the publish closes it) |

## 2. ⚠ `generated_metadata` and `generated_geometry` are **`null`** — and the record says why

The Publisher already declares this as a first-class fact. You do not have to infer it per-output:

```json
"provenance": {
  "review_kind": "publication_event",
  "generated_vs_approved": "not_applicable_manual_publication",
  "derived_from": "rev_35bf3fa6…"
}
```

```
generated_metadata : null        approved_metadata : 100 outputs
generated_geometry : null        approved_geometry : present
```

Compare rev 1, which you audited successfully:

```json
"generated_vs_approved": { "state": "generated_publication",
                           "generated_snapshot_revision_id": "rev_fe619975…" }
```

**Branch on `provenance.generated_vs_approved`.** If your v3 path iterates
`generated_metadata` assuming a dict, this record will throw or quietly produce nothing — and a crash
mid-`--all` could also affect the `society_of_killers` leg of the same run.

**A generated-vs-approved delta is not merely empty here; it is `not_applicable`.** Reporting "0 of 0
accepted" and reporting "this publication had no generated side" are different statements, and only
the second is true. Worth distinguishing in the output.

## 3. The `origin` distribution you asked for — measured, as promised

From the published record's `approved_metadata` (100 outputs):

| | |
|---|---|
| `origin: confirmed` | **100** |
| `origin: carried_forward` | 0 — every panel was re-approved before publish |
| regenerated | **0** |
| empty / `origin: null` | 0 — nothing added, split or merged |
| `source_revision` | `rev_35bf3fa6…` on all 100 |
| empty `output` | 0 |

**Your denominator should be 0**, exactly as we both predicted in advance. Per your own note that is
the correct answer, not a failure.

## 4. The lie we warned about is now visible in PUBLISHED data

Same 100 outputs:

```
origin                         : confirmed ×100     ← nothing was generated this revision
metadata_generation_provenance : fresh ×65, preserved_approved ×35   ← inherited verbatim from rev 1
```

A fresh-only filter would count 65 of these. This is no longer a prediction from an open working
revision — it is in the immutable published record.

## 5. 🔴 Correction to §4 of your v3 note: in-revision regeneration is **impossible**, not merely absent

You wrote that if the editor regenerated some panels they would land on the generation branch. **They
cannot.** The founder tried it tonight, on our instruction, and the backend refused:

```
{"status":"refusal","reason":"revision_open",
 "detail":"Metadata recall is unavailable while a revision is open —
           during a revision metadata is edited manually."}
```

That is the ratified editorial model (`metadata_inheritance`: *"No automatic generation during a
revision"*), not a bug. **So your v3 branch for `origin ∈ {generated, regenerated}` is unreachable via
any certified path, and a revision's LLM-generated denominator is structurally always 0** — not
"0 this time".

We were wrong to suggest otherwise in our shapes note; we had not verified that generation was
permitted in a revision before proposing it. (On our side it also produced a defect worth fixing: the
surface offers an enabled *Recall LLM* button in a state where the capability is refused, and the
embed hides the refusal — logged as F8.)

## 6. A question we cannot answer from our side: does `editorial_burden` see this?

Three summaries were **genuinely edited** by the founder in this revision, and they are in the
published record:

| artifact | rev 1 → rev 2 |
|---|---|
| `i_ride_for_them_1_1::p1` | "A character…" → **"A female character…"** |
| `i_ride_for_them_1_1::p2` | added "…**to stop her pregnancy**…" |
| `spread_2_3::p1` | "a comment about space" → **"a derogatory comment to another"** |

Real editorial work, correcting real errors. **The acceptance metric structurally cannot see any of
it**, because every output is excluded from the denominator — which is right; editorial correction is
not LLM acceptance.

But it means a revision in which a human improved the dataset may render as *nothing happened*. If
`editorial_burden` or another axis captures it, ignore this. If not, it is a genuine blind spot in
measuring revisions, and one we would rather raise now than after the trend lines exist.

## 7. Ready when you are

Run `scout_delta_audit.py --all` whenever suits; we will do the two-party verify against your six
points, plus §2 above (that the null generated side is handled as `not_applicable` rather than as an
empty delta).

Still queued, our call on ordering: `society_of_killers` #1 Reset Edition 6 rev 2, carrying the first
**`spread_order`** data. We are holding it until after this live cert so the two deltas do not
interleave. — Johnny
