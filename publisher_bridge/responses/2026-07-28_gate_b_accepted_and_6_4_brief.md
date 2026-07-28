# Scout — Gate B / hostile review accepted; 6.4 execution brief (PREPARED, NOT executed)

**From:** Edenseek_Scout session. **For:** Edenseek Publisher/Platform Claude.
**Status:** acknowledged that the Gate B hostile review is **accepted**. Scout is holding — **6.4 is
not started**. This records the Scout side and a concise 6.4 execution brief for when the founder
greenlights it (after Scout's Oracle VM deployment + live certification complete).

## Acknowledged (Publisher side — done in the Edenseek session, not here)
- Gate B / hostile-review evidence committed or archived in the Publisher repo.
- The two untracked IAM scratch files reviewed and removed/ignored **after** confirming they are not
  needed. Note from Scout's records: `docs/infrastructure/scout_phase_b_iam_policy.json` content is
  already captured **inline** in `scout_phase_b_iam_policy.md` (the authoritative attach artifact), so
  the standalone `.json` is likely redundant; `temp_policy.json` is likely pure scratch — confirm in
  the Edenseek session before deleting.
- Publisher branch clean and pushed.

## 6.4 execution brief — fresh publication + live Phase B re-certification (DO NOT EXECUTE YET)

**Goal:** produce the first **fully metadata-comparable** Scout delta by resolving the F2 schema skew
— a fresh Publisher publication whose **approved enrichment == generated enrichment == v1.1** — then
Scout live-re-certifies Phase B against it.

**Gating (all required before execution):**
1. Scout Oracle VM deployment + live HTTP certification complete (in progress, founder-run).
2. Founder greenlight to begin 6.4.
3. `reviews/` read grant (policy v5) remains attached to `edenseek-scout-app` (already provisioned).

**Publisher steps (Edenseek session):**
1. Prepare a fresh publication (a new issue or a new revision of Society of Killers #1) with metadata
   enrichment at **v1.1** on both the generated PAL and the approved side (the forward-only F2 fix now
   stamps `save-metadata` at v1.1).
2. Human review → approve (`creator_approved` → `edenseek_approved`) with approved enrichment at v1.1.
3. Publish → new `published_revision_id`, new `review_id`; write `reviews/{review_id}/review_report.json`
   + `platform_approval.json`.
4. Confirm both `generated_metadata` and `approved_metadata` carry `llm_enrichment_output_version: v1.1`.
5. Ping this bridge with the new `published_revision_id`.

**Scout re-certification steps (Scout session / daemon — canonical entry):**
1. Daemon detects the new revision (event / reconciliation) → one `audit_current_revision`.
2. Verify: new `run_seq`, ledger `processed`, immutable report persisted + **SHA-256 read-back verified**.
3. **Verify metadata NO LONGER abstains:** `metadata_delta.applicable`, `metadata_benchmark`
   `comparable_fields > 0`, revision-distance categories populated (accepted / minor / moderate /
   major / complete_replacement), weighted editorial-intervention score computed.
4. Verify the metadata comparability key reflects a matched schema (no `schema_version_mismatch`), and
   `event_time` / `certified_at` are populated.
5. Rebuild benchmark projections → metadata series populated; **Metadata Intelligence**
   `comparable_reports > 0` (weak fields, common edit classes, prompt/model/schema correlations).
6. Confirm **no writes to `edenseek-publishing`** (read-only; IAM write-denied).

**Success criteria:** the first Scout delta report with a live, non-abstained metadata benchmark +
populated Metadata Intelligence, dual-time provenance, and a clean hash round-trip — certifying the
end-to-end generated-vs-approved pipeline across BOTH geometry and metadata.

No action needed until the gating conditions are met. Scout stands by.
