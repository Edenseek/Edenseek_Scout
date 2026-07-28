# Week 11 — Scout Phase B Live Certification (Increment 6.3)

> **Result: CERTIFIED (2026-07-27).** Scout's Synchronization Audit (generated-vs-approved delta)
> runs end-to-end against the **production** `edenseek-publishing` repository as the least-privilege
> `edenseek-scout-app` identity, over the certified revision `rev_a8c65a83a196` (Society of Killers
> Issue 1). IAM access matrix verified; anti-corruption boundary accepts real emitted bytes;
> delta is coherent and byte-deterministic. Read-only throughout — Scout wrote nothing to
> `edenseek-publishing`.

Identity exercised: `arn:aws:iam::275896269087:user/edenseek-scout-app` (policy
`EdenseekScoutPublishingReadAccess` v5, per `Edenseek/docs/infrastructure/scout_phase_b_iam_policy.md`).
Credentials override the machine admin profile via `.env`; Scout never ran as admin.

## Part 1 — IAM access matrix (9/9 PASS)

| # | Check | Expect | Result |
|---|---|---|---|
| 1 | `approved/` GetObject `published.json` | ALLOW | ✅ 200 |
| 2 | `processing/` GetObject `workspace/{rev}/processing_snapshot.json` | ALLOW | ✅ 200 (550 KB) |
| 3 | `reviews/` GetObject `review_report.json` | ALLOW | ✅ 200 (340 KB) |
| 4 | `reviews/` GetObject `platform_approval.json` | ALLOW | ✅ 200 |
| 5 | `registry/` GetObject `dataset_registry.json` | ALLOW | ✅ 200 |
| 6 | `ListBucket` (issue prefix) | ALLOW | ✅ 200 (KeyCount 400) |
| 7 | `PutObject` to `edenseek-publishing` | **DENY** | ✅ 403 AccessDenied |
| 8 | `intake/` GetObject | **DENY** | ✅ 403 AccessDenied |
| 9 | `reference/` GetObject | **DENY** | ✅ 403 AccessDenied |

The hard write-boundary and the `intake/`+`reference/` read-exclusions hold; the four audit
surfaces + registry are readable exactly as the v5 policy specifies. `review_id` was derived
deterministically from the published pointer (`rev_a8c65a83a196`) — no `ListBucket` required for the
delta path.

## Part 2 — Live delta certification (production `rev_a8c65a83a196`)

The **same** adapter + delta code unit-certified in Phase A, run over the live Review Record (C) +
Platform Approval (D). Inputs: 51 generated panels; 97 approved artifacts (36 page + 48 NEW + 13
spread) + 2 structural sibling keys.

- **applicability:** `generated_publication`
- **Geometry delta:** precision **0.941**, recall **0.608**, split_rate **0.577**, merge_rate
  **0.902**, missing_page **4**, spread_missing **34**, false **3**.
- **Metadata delta:** **abstained** — generated enrichment schema `v1.1` vs approved `v1` ⇒ all 97
  artifacts `schema_version_mismatch`, 0 compared (correct schema-scoped behavior; see finding F2).
- **Correction ledger:** 240 entries (geometry: 56 split, 46 merge, 34 spread-missing, 4 missing, 3
  false; metadata: 97 schema-version-mismatch).
- **Publisher certified state:** `edenseek_approved`, `readiness.passes_integrity=true` — carried
  **verbatim** and kept **separate** from Scout's independent delta (`canonical_dataset_state` absent
  from the geometry/metadata deltas, as required).
- **Determinism:** two runs serialize **byte-identical** (72,388 bytes).

## Findings surfaced by the live run

**F1 — `approved_geometry` structural sibling keys (RESOLVED in Scout).** Production
`approved_geometry` mixes non-panel structural keys (`panel_order` dict, `spread_artifacts` list)
into the `artifact_id` map. The fail-fast anti-corruption boundary correctly refused to reinterpret
them. Scout now **skips the known structural keys and fails fast on any other non-artifact member**
(`review_contract_adapter.APPROVED_GEOMETRY_STRUCTURAL_KEYS`); regression tests added; contract §5
updated. No Publisher change required.

**F2 — metadata schema-version skew `v1.1` (generated) vs `v1` (approved) → PUBLISHER QUESTION.**
Because the two enrichment sets declare different `llm_enrichment_output_version`s, Scout's
schema-scoped comparability excludes every artifact and the metadata field delta abstains. This is
Scout behaving correctly (it will not compare across a declared schema boundary). **Open question for
the Publisher/Platform:** is the `v1.1`→`v1` skew expected, and are the two versions intended to be
content-comparable? If yes, either align the versions or publish a compatibility declaration so Scout
can compute the metadata delta; if no, this is a real pipeline-versioning signal worth investigating.
Flagged via the bridge. Scout does **not** relax comparability unilaterally.

**F3 — high geometry split/merge rates (OBSERVATION).** merge_rate 0.902 / split_rate 0.577 reflect
that the 51 automated panels are coarser than the 97-artifact human-approved set (many NEW + spread
panels have no automated counterpart). Plausibly genuine under-segmentation intelligence; noted for
Publisher review, not a certification blocker.

## Scope / boundaries held
Read-only (`GetObject`/`ListBucket` only); no write to `edenseek-publishing` (attempted PutObject
denied by design). Deterministic, offline delta (no LLM/vision/network beyond the S3 reads). Scout
reports the Publisher's certified state verbatim and computes its own delta independently — it sets,
gates, and approves nothing.

## Status
- Phase B **live-certified** for `rev_a8c65a83a196`. Access matrix + delta pipeline both green.
- Follow-ups: (a) Publisher answer on F2 (metadata schema skew); (b) optional productionization —
  wire the `reviews/` reader into `audit_s3_source` and persist the live delta report to
  `edenseek-scout` on the revision-watch trigger (this cert fetched the two `reviews/` objects
  directly). Neither blocks the Week 11 certification.
