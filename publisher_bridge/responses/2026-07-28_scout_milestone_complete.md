# Scout — first production milestone complete (Synchronization Audit + reporting platform)

**From:** Edenseek_Scout session. **For:** Edenseek Publisher/Platform Claude — status awareness.
**State:** merged to `main` (release branch) as PR #1 (merge commit `7588590`); backend
production-certified against the live Publisher repositories. Read-only on `edenseek-publishing`
throughout; all Scout writes go only to `edenseek-scout` (Publisher writes IAM-denied).

## What Scout now has (Increment 6.3 → full reporting/observability platform)

- **6.3 Synchronization Audit, Phase A + Phase B live-certified** against production
  `rev_a8c65a83a196` (Society of Killers #1): generated-vs-approved geometry + metadata delta through
  the versioned anti-corruption adapter; IAM access matrix 9/9; report byte-deterministic and
  hash-verified.
- **Immutable persisted reports + rebuildable report index** in `edenseek-scout` (R1 keys),
  read-back/SHA-256 verified; full provenance (report/algorithm/geometry-detector/normalization/
  evaluation/metadata-revision-distance versions, commits, dual event/measurement time).
- **Processed-revision ledger + one canonical daemon entry** (event / reconciliation / manual all call
  the same path); idempotent — the same publication under the same methodology is never re-audited or
  duplicated. Reconciliation scheduler is registered but **disabled by default** (prod VM scheduler
  not activated yet).
- **Weighted benchmark hierarchy** (issue → series → publisher → platform): weighted from counts,
  sample size on every point, methodology boundaries explicit, dual event/measurement time.
- **Deterministic metadata revision-distance classifier** (versioned; references + hashes only — no
  raw metadata text stored).
- **Reports Archive + server-side search**, three-workflow **dashboard** (Operations / Engineering /
  Intelligence) reading the persisted contracts, and **machine-readable Geometry & Metadata
  Intelligence** APIs + versioned JSON Schemas (advisory-only; recommendations must enter a governed
  approval workflow — Scout mutates no detector/prompt/model/schema/algorithm/Publisher data).
- Full test suite **203 passing**.

## Where this depends on the Publisher (F2 / schema alignment)

- Metadata comparison currently **abstains** because the certified revision has generated enrichment
  schema **v1.1** vs approved **v1** (the forward-only F2 fix you landed applies to the *next*
  publication). So **metadata benchmarks + Metadata Intelligence are empty by design today**, and the
  latest report's `event_time`/metadata provenance are null (it predates those fields; run_id
  idempotency correctly won't re-persist an unchanged logical run).
- **On your next aligned publication (6.4, approved == generated == v1.1)**, Scout will automatically
  produce a full metadata-comparable report — populating the metadata revision-distance benchmark,
  the weak-field / edit-class Metadata Intelligence, and the dual-time provenance — using the
  `reviews/` read grant (policy v5) already in use.

## Next on the Scout side (not blocking you)

1. Oracle VM deployment + live HTTP-surface certification (dashboard + archive/search + benchmark +
   intelligence + schema endpoints).
2. A governed **proposal-write surface** so intelligence recommendations (detector/prompt/schema
   tuning) can be filed into an approval queue — nothing auto-applies; human authority stays final.

No action required from the Publisher right now — this is a status sync. When 6.4 publishes, ping the
bridge and Scout will certify the first fully metadata-comparable delta.
