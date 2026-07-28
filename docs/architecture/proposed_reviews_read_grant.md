# PROPOSAL — Scout read grant for `reviews/` (Increment 6.3, §6)

> **Status: PROPOSAL for the Publisher/Platform governance side. NOT applied from Scout.**
> Cross-repository read access is Platform/Publisher governance. Scout **proposes** the
> contract amendment and IAM policy below; it does **not** implement Publisher infrastructure
> or modify the Publisher repository. This document lives in the Scout repo as the proposed
> text to be ratified in `Edenseek` (`docs/architecture/scout_data_access_contract.md`) and
> provisioned on the `edenseek-publishing` IAM by the Publisher/admin.

## Why
Scout's generated-vs-approved delta (6.3) needs the **Review Record (C)** and **Platform
Approval (D)**, which live under `reviews/{review_id}/`. The authoritative generated↔approved
**LINK** lives *only* in C, and the canonical-state signal lives *only* in D. Scout's current
Publishing-repo read scope is `approved/`, `registry/`, `processing/` — `reviews/` is not
read-permitted (it is already write-prohibited). Without this grant, Scout can compute a delta
from A + B but cannot obtain the per-publication link or the canonical-state signal. This is a
**Phase B** prerequisite; Phase A (offline, fixture-based) needs nothing.

## Scope (least privilege, read-only)
Grant Scout **read-only** access to exactly two objects per review:
- `.../issues/{issue_id}/reviews/{review_id}/review_report.json`
- `.../issues/{issue_id}/reviews/{review_id}/platform_approval.json`

No write, no delete, no other `reviews/` object, no listing beyond what is needed to resolve
`{review_id}` (which Scout derives deterministically from the published pointer — no scan
required).

## (a) Proposed amendment to `scout_data_access_contract.md` (Publisher repo)

Add to the permitted Publishing-repo reads for the Approved-Dataset / Canonical phases:

> Scout may additionally read, **read-only**, the two per-publication certification artifacts
> under the issue's `reviews/{review_id}/` surface — `review_report.json` (the Review Record,
> carrying the generated and approved sides plus the authoritative generated↔approved link) and
> `platform_approval.json` (the Platform Approval, carrying the canonical dataset state and the
> platform readiness attestation). `review_id` is derived deterministically from
> `approved/published.json`. No other `reviews/` object is Scout-readable; `reviews/` remains
> write-prohibited. Scout consumes these as an independent verifier and reports on them; it
> never sets canonical state, gates a phase, or approves.

## (b) Proposed IAM policy (Publisher-facing) — attach to the Scout read identity

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ScoutReadReviewCertificationArtifacts",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion"],
      "Resource": [
        "arn:aws:s3:::edenseek-publishing/publishers/*/title_groups/*/series/*/issues/*/reviews/*/review_report.json",
        "arn:aws:s3:::edenseek-publishing/publishers/*/title_groups/*/series/*/issues/*/reviews/*/platform_approval.json"
      ]
    }
  ]
}
```

- **Read-only** (`GetObject`/`GetObjectVersion` only) — no `Put`, no `Delete`, no `ListBucket`.
- Scoped to exactly the two object names under any `reviews/{review_id}/`; no other `reviews/`
  object is reachable.
- Consistent with the Repository Ownership Principle: Scout reads certified Publisher artifacts;
  it writes only to `edenseek-scout`.

## What Scout will NOT do
Scout will not create, modify, or apply this policy; will not edit
`scout_data_access_contract.md` in the Publisher repo; and will not read `reviews/` until the
grant is provisioned. Until then, 6.3 remains at **Phase A** (offline, unit-certified).
