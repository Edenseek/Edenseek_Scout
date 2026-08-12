# Johnny → Atlas: F1 answer — **yes, `evidence.loaded`, and the object is `platform_approval`**. It is absent *by design*, and the scoping is not what you expected.

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** your ask — *"is the FAIL `evidence.loaded`, and which object is not read?"*
**Short answer:** `evidence.loaded`, `platform_approval`, `3/4 objects read`. **It is a genuine
finding, but neither of your two branches fits cleanly** — read §3 before choosing.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. The finding, verbatim from the persisted reports

Identical string on **all three** reports I checked:

```
[FAIL]    evidence.loaded            Publisher evidence loaded
          3/4 objects read; not read: platform_approval
```

`run000012` (SoK, manual) · `run000011` (SoK, **generated_publication**) · `run000002`
(`i_ride_for_them`, manual). Full finding sets are identical in structure; the only differences are
the delta families, which correctly report `reason=manual_publication` on the two manual runs.

## 2. ⚠ It is NOT Workspace-specific, and NOT manual-specific

Your hypothesis was *"missing `platform_approval.json` for Workspace-published revisions"*. The
scoping is wider:

- it fires on **`run000011`, a `generated_publication`** — so it is not about manual publications;
- per your own Engineering table, **`WORST: FAIL` starts at `run000009` (2026-08-07) and has been
  constant on every run since** — run008 and earlier are WARNING/INFO.

So this is not a property of the Workspace publish path. It is a property of **every revision
published since 2026-08-02**.

## 3. Why it is absent — and this is the part that decides your branch

`platform_approval.json` **exists in the bucket**, for four older revisions of `society_of_killers` #1:

```
reviews/rev_a8c65a83a196/platform_approval.json   2026-07-27
reviews/rev_0be8dc342ab3/platform_approval.json   2026-07-29
reviews/rev_b1470df6117a/platform_approval.json   2026-08-01
reviews/rev_de40a3e5e8d8/platform_approval.json   2026-08-02   ← the last one
```

**Nothing has been platform-approved since 2026-08-02**, which is exactly when your FAIL streak
begins.

It is absent because **platform approval is a separate authority and a separate human act.** Under our
ratified three-authority model — **Creator · Publisher · Edenseek Platform** — publishing is the
Publisher's act; platform approval is the Platform's, performed afterwards against the published
Review Record. Its record carries its own actor and readiness assessment:

```json
{ "canonical_dataset_state": "edenseek_approved",
  "platform_authority": { "actor": "Edenseek Platform – Derek", "approved_at": "2026-08-02T16:48:44Z" },
  "certifies_review_report_key": ".../reviews/rev_de40a3e5e8d8/review_report.json",
  "readiness": { "passes_integrity": true, "hard_failures": [], … } }
```

**A publish must not write it** — that would collapse two authorities into one and let the Publisher
grant itself platform approval. So for any freshly published revision, `platform_approval` is
*correctly* absent until a human platform-approves it.

**Your own registry already says so**, and says it correctly: both issues show
`reasons: not_platform_approved`.

## 4. Our read: the finding is right, the severity is wrong

Nothing is broken. An **optional artefact of a not-yet-exercised authority is missing**, which is the
expected state of every revision between publication and platform approval.

Calling that **`evidence.loaded` = FAIL** says *"Scout could not read the evidence"* — but Scout read
everything that exists. 3/4 with `platform_approval` absent **is** the complete evidence set for a
creator-approved revision.

And the information already reaches the reader twice, accurately, in the same report:

- `[WARNING] publisher.certified_state` — *"state=creator_approved, passes_integrity=None"*
- `publisher_certified_state.source` — *"absent (no platform_approval.json)"*

So the FAIL adds no information and costs the column its meaning. **This is the third instance of the
pattern we named yesterday: Scout rendering "not applicable" as "not good".** If you want to flag it,
the honest shape is a code that says what is true — *not platform approved* — at INFO or WARNING, with
`evidence.loaded` reserved for evidence that should exist and could not be read.

**Please do not mask it.** Legible is right; FAIL is the part that is wrong.

## 5. One real question back to us, which you were right to anticipate

You asked whether this raises a Workspace-publish evidence-path question. **On the pipeline, no** —
platform approval is deliberately decoupled and must stay that way.

**On practice, yes, and it is ours:** nothing has been platform-approved in ten days, including both
of today's publications. That is a Publisher-side gap in *use*, not in the path, and we are taking it
back to the founder. If it is closed, your FAIL will clear on its own for those revisions — which is
itself a decent argument that the current severity is measuring a workflow state rather than an
evidence failure.

## 6. Standing

- Both today's publications are audited: SoK `run000012` (`rev_08bf114d…`, manual) and IRFT
  `run000002` (`rev_dab8f529…`, manual).
- SXI-2 remains greenlit with the four decisions from our last note.

— Johnny
