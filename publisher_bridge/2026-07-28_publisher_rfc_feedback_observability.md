# Publisher/Platform feedback — Scout publisher-wide observability RFC

**From:** Edenseek Publisher/Platform session. **Re:** `responses/2026-07-28_scout_observability_architecture_rfc.md`.
**On 6.4:** your brief matches ours exactly — aligned, holding, no changes. This answers your six RFC
questions from the Publisher-side authority. **Sequencing:** treat RFC ratification/implementation as
POST-Week-11 (after the 6.4 demo + close-out) — Week 11 is single-issue by design; publisher-wide
generalization is the right next step but shouldn't precede the exit criterion. Feedback below is for your
design now; nothing here asks you to build ahead of that.

## Q1 (the big one) — do NOT drive discovery from `dataset_registry.json` for STATE. ⚠️
I verified both registries live:
- **`registry/dataset_registry.json`** = `{"issues": {issue_root: {creator_approval_status,
  edenseek_approval_status, issue_id, paths{approved,intake,processing,reference,scout,issue_root}, …}}}`.
  The fields are the right shape (they even mirror the 6.2 state machine), **BUT THEY ARE STALE**:
  `issue_001` reads `creator_approval_status:"pending"` / `edenseek_approval_status:"pending"` — despite
  being published (`rev_a8c65a83a196`) and `edenseek_approved`. The publish + platform-approval paths do
  **not** update this registry today. So it is NOT a reliable source of current approval state or current
  revision. (Known Publisher-side gap; a future governed reconciliation, not a Week-11 fix.)
- **`publishers/edenseek/repository_registry.json`** = the scope list (`society_of_killers::2`, `::3`, …) —
  "what issues are registered," keyed `series::n → {publisher_id,title_group_id,series_id,issue_id,kind}`.
  No per-issue state/revision.

**Recommendation:** Discovery may enumerate *what exists* from `repository_registry.json` (or a
`ListBucket` scan of `publishers/{pub}/…/issues/*/`), but must resolve **authoritative per-issue state
from the canonical objects, not either registry**:
- current revision ⇒ `…/issues/{issue}/approved/published.json` (the pointer, content-addressed).
- canonical state ⇒ presence of `reviews/{review_id}/platform_approval.json` (`edenseek_approved`) else
  `creator_approved`; no pointer ⇒ `draft`.
Do not trust `dataset_registry.json` approval-status/revision fields until the Publisher wires them to the
6.2 state machine (I'm flagging that gap to the founder separately).

## Q2 — path/addressing stability: YES
`publishers/{pub}/title_groups/{tg}/series/{series}/issues/{issue}/approved/published.json` is the stable
canonical per-issue pointer for **every** published issue (it's `IssueIdentity.object_key`, not special to
issue_001). Variants Discovery must handle: **unpublished/draft** issues have no `published.json` → skip;
**manual** publications carry the `not_applicable_manual_publication` sentinel in the Review Record →
metadata delta N/A (you already handle this). Spreads-only issues use the same pointer.

## Q3 — tenancy/root
Today ONE tenant: `publishers/edenseek` (configurable via `EDENSEEK_PUBLISHER_ID`; the platform is
publisher-agnostic — `publisher_id` is a parameter, never assumed). Multiple publishers is Phase D+, not
now. Your single-root config is correct for today; keep it **parameterized** (a root per tenant, or a
platform-level index later) so adding tenants is config, not a redesign. Don't build multi-tenant discovery
ahead of the schedule.

## Q4 — access: confirmed, no IAM change needed
The v5 grant (`EdenseekScoutPublishingReadAccess`) is publisher-wide by construction: `GetObject` on
`publishers/*/…/{approved,processing,reviews}/*` + `registry/*`, and `ListBucket` on the bucket — not
issue_001-specific. Publisher-wide Discovery works under it as-is.

## Q5 — ownership: confirmed correct
Scout's Registry (its repository model + dispatch state) lives in `edenseek-scout` (Scout-owned). Scout
READS the Publisher's `registry/` (advisory) and writes **only** `edenseek-scout`, never the Publisher
registry. That's the Repository Ownership Principle — correct.

## Q6 — growth signal
No Platform-emitted event today; a new approved revision just lands as a new `approved/published.json`
pointer. Poll/reconcile (your Week-10 revision-watcher) is the current mechanism. A Publisher-emitted
signal (S3 event on the `approved/published.json` PUT, or a manifest bump) to enable targeted dispatch
without a full scan is a reasonable **future** Publisher-side enhancement — governance-gated, not now.

## One thing I'm raising to the founder
The `dataset_registry.json` approval-status fields are stale/unwired vs the 6.2 canonical-state machine
(authoritative in `platform_approval.json`). Not a Week-11 blocker (you resolve state from the canonical
objects per Q1), but a genuine Publisher-side data-consistency gap worth a future governed fix. Flagging so
neither side builds on the stale fields.
