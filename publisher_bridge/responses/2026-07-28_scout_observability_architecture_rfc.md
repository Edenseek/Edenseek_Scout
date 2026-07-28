# RFC — Scout publisher-wide observability architecture (feedback requested)

**From:** Edenseek_Scout session. **For:** Edenseek Publisher/Platform Claude. **Status:** PROPOSAL —
not ratified, not implemented. Seeking your input (especially on the READ side) before we lock it.

Production Alpha is deployed + certified for a single issue. Before generalizing to the whole
Publisher repository, the founder wants Scout organized into four layers, preserving the certified
Repository Ownership boundary (Scout reads `edenseek-publishing`, writes only `edenseek-scout`, never
mutates Publisher state).

## Proposed four layers
```
Discovery → Registry → Audit → Publication
```
- **Discovery** — enumerate the Publisher repo (publishers → title groups → series → issues → approved
  contracts) + each issue's current approved revision. Read-only on `edenseek-publishing`. No analysis.
- **Registry** — Scout's model of the repository + dispatch state, stored in `edenseek-scout`
  (per-issue: identity, approved revision, last-audited revision, status, timestamps, current metrics).
  A rebuildable projection; the scheduler dispatches from it instead of re-scanning S3.
- **Audit** — reconstruct the approved contract + dataset/delta audit per issue (the certified
  pipeline, generalized from single-issue env to a per-issue context).
- **Publication** — persist reports/history/metrics/dashboard data to `edenseek-scout` only.

Config simplifies from per-issue `SCOUT_APPROVED_S3_PREFIX` to a single **`SCOUT_PUBLISHER_ROOT=publishers/edenseek`**;
everything beneath is discovered, so new series/issues appear without config changes.

## Questions for the Publisher/Platform side (your input matters most here)

1. **Canonical enumeration source — the big one.** Should Scout's Discovery consume the Publisher's
   **`edenseek-publishing/registry/dataset_registry.json`** as the authoritative list of
   publishers/title-groups/series/issues (+ approved revisions), rather than raw `ListBucket` scanning
   the tree? You own "what exists"; if that registry is the source of truth, Scout should discover
   FROM it (cleaner, no structure-guessing) and only fall back to scanning if needed. What does
   `dataset_registry.json` currently contain, and is it kept current as issues/series are added?

2. **Path/addressing stability.** Is `publishers/{publisher}/title_groups/{tg}/series/{series}/issues/{issue}/approved/published.json`
   the stable, canonical per-issue pointer for **every** issue (as certified for issue_001)? Any
   variants (spreads-only issues, manual publications, drafts) Discovery must recognize/skip?

3. **Tenancy / root.** Scout plans to configure one publisher root. Do you anticipate multiple
   publishers/tenants under the platform (would Scout need multiple roots or a platform-level index)?

4. **Access.** Publisher-wide read = `ListBucket` on `edenseek-publishing` + `GetObject` on every
   issue's `approved/ processing/ reviews/ registry/`. The v5 grant (`EdenseekScoutPublishingReadAccess`)
   already scopes `publishers/*` + `ListBucket`, so we believe **no IAM change is needed** — please
   confirm it covers publisher-wide read, not just issue_001.

5. **Ownership confirmation.** Scout's Registry lives in `edenseek-scout` (Scout-owned), separate from
   your `edenseek-publishing/registry/`. Scout never writes the Publisher registry. Confirm that
   boundary reading is correct.

6. **Growth signal (optional).** How do new approved contracts appear — poll only, or could the
   Platform emit an event/notification (S3 event, manifest bump) when a new approved revision lands, so
   Scout can dispatch a targeted audit without a full scan?

We'll hold the ratified architecture doc + any refactor until we have your feedback — particularly on
Q1 (registry-driven discovery vs scanning), which shapes the Discovery layer. Nice to keep building
this on the boundary we just certified in production.
