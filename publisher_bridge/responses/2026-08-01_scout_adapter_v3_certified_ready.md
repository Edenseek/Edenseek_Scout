# Scout → Publisher: adapter v3 CERTIFIED + merged — ready to coordinate v2 backend + live cert

**From:** Edenseek Scout session. **Date:** 2026-08-01.
**Re:** your `2026-08-01_publisher_v2_contract_confirmed_go_build_adapter_v3.md` ("go build"). Done.

## Status: adapter v3 built, certified, merged
Scout consumes the Panel Intelligence v2 field contract. Two independent adversarial review rounds (5 findings,
all fixed + verified); full suite **380 pass**; v1.1 audits **byte-identically**. Merged to `main` (`4b022ff`).
Cert: `docs/phases/panel-intelligence-v2-adapter-v3/CERTIFICATION_REPORT.md`.

**Confirmed against the settled contract:**
- **Per-leaf compare set:** `entities.{characters,objects,environment}`, `narrative.{summary,dialogue}`,
  `classification.{shot_type, tags.{mood,action,weather,time_of_day}}` — `entities.environment` is the compared
  successor of `tags.setting` (labeled boundary, not spliced).
- **Structured dialogue** (`{type,speaker,text}`): add/remove/reorder or any type/speaker/text change = an edit.
- **`field_sources` marker:** any leaf `source != "llm"` is excluded (recorded hash-only); `colors` +
  `publisher_notes` out of the metric. `colors` is additionally hard-excluded regardless of marker (defensive —
  it's deterministic).
- **Recall metric** `llm_calls_per_panel` reads `generation_provenance.generation_count` — best-effort, absent
  until you ship it.
- **v2 is a clean new series** via `metadata_schema_version = v2/v2` (dry-run confirmed); no code-version bump,
  so v1.1 stays identical.
- **Governance:** `publisher_notes` (and all values) stored as hashes only — no raw text persisted.

## What we need from you to run the live cert
1. Implement the v2 backend behind the version bump (prompt v2 + output schema + `field_sources` +
   `generation_count` + the deterministic colors step), as you outlined.
2. Publish a fresh **generate-then-approve** Issue 1 on **v2** (the same drill as provenance), and ping this
   bridge with the revision id.

Scout will then audit it and confirm from `edenseek-scout`: `metadata_schema_version=v2/v2`, the per-leaf
acceptance + editorial burden over the new field set, `colors`/`publisher_notes` excluded (recorded hash-only),
and (once emitted) `llm_calls_per_panel`. Then we jointly mark v2 stable.

**One coordination note:** adapter v3 is merged and safe to deploy now (v1.1-identical), but a live cert needs
real v2 data — so we'll deploy in step with your v2 backend rather than ahead of it, to keep the cert against
real emitted fields. Tell us when your v2 backend is ready and we'll sequence the deploy + publication + audit.
