# D2 — `reviews/` read grant proposal (Publisher/Platform governance)

**Owner:** Publisher/Platform (the `edenseek-publishing` repository owner). **For:** founder approval +
provisioning. Scout may review/comment; Scout does NOT implement this (it is IAM/governance, not Scout
code). This is the Publisher/Platform-side counterpart to Scout's drafted `proposed_reviews_read_grant.md`.

## Why

Scout's 6.3 delta + canonical-state sync require reading two objects that live in the platform-reserved
`reviews/` layer of `edenseek-publishing`:
- `…/issues/{issue}/reviews/{review_id}/review_report.json` (the generated↔approved link + both sides)
- `…/issues/{issue}/reviews/{review_id}/platform_approval.json` (canonical state = edenseek_approved)

Scout's current Publishing-repo read scope is `approved/`, `registry/`, `processing/` — it does **not**
include `reviews/`. Scout derives `review_id` deterministically from the published pointer
(`review_id = "rev_" + published_revision_id.split("_",1)[1][:12]`), so it can `GetObject` the two keys
directly — **no `ListBucket` needed**.

## (a) Data-access-contract amendment (Publisher repo: `docs/architecture/scout_data_access_contract.md`)

Additive, to be applied Publisher-side (captures existing architecture; the contract already sanctions the
Review Report as "a permitted Scout read"). Proposed text:

> **`reviews/` (Approved-Dataset / Canonical phases).** For a published revision, Scout may read
> `reviews/{review_id}/review_report.json` (the completed-review composition — generated + approved
> geometry/metadata + the `generated_vs_approved` link) and `reviews/{review_id}/platform_approval.json`
> (the Edenseek Platform Authority certification + canonical-dataset state). Read-only, for the
> generated-vs-approved delta audit and canonical-state reporting only. Scout reads no other `reviews/`
> object and writes nothing. `review_id` is derived from the published pointer's `revision_id`.

## (b) IAM policy — least-privilege read for `edenseek-scout-app`

Add to the `edenseek-scout-app` identity's policy (extends its existing read on `edenseek-publishing`
`approved/` + `registry/` + `processing/`). Object-scoped to exactly the two file names, any issue:

```json
{
  "Sid": "ScoutReadReviewsLayerReviewAndPlatformApproval",
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": [
    "arn:aws:s3:::edenseek-publishing/publishers/*/reviews/*/review_report.json",
    "arn:aws:s3:::edenseek-publishing/publishers/*/reviews/*/platform_approval.json"
  ]
}
```

Notes:
- **No `ListBucket`** — Scout computes the keys deterministically; listing is unnecessary and withheld
  (least privilege).
- **No write** anywhere in `edenseek-publishing` — unchanged; Scout writes only to `edenseek-scout`.
- Scoped to the two object names, so it cannot read `saved_geometry.json`, `approval_state.json`, or any
  other workspace/pre-approval object, even under `reviews/`.
- Publisher-agnostic: `publishers/*` covers any tenant, consistent with the platform being publisher-
  agnostic; the `*` is the identity's tenant segment, not a Publisher assumption.

## Sequencing (matches D3)

Scout Phase A (build + fix + unit tests on `real_shape_samples.json`) needs **none** of this. Provision
(a) + (b) only before Scout Phase B (live certification against production `reviews/`). Until then Scout
must not attempt live `reviews/` reads (it will get AccessDenied by design).

## Verification after provisioning (recommended)

- Positive: `edenseek-scout-app` can `GetObject` the two `reviews/…` keys for the certified revision.
- Negative (least-privilege proof): the same identity is DENIED `GetObject` on a `reviews/…` object other
  than those two names, DENIED `ListBucket` on `reviews/`, and DENIED any `PutObject` to
  `edenseek-publishing`.
