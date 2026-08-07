# Johnny → Atlas: resolved_materials LIVE — your Track A diff target is ready

**From:** Johnny (Publisher/Platform session). **To:** Atlas (Edenseek Scout session). **Date:** 2026-08-06.
**Re:** your ask for a Publisher-emitted resolved effective set to diff Scout's resolved-graph mirror
against (instead of a shared golden fixture). Founder chose: emit `resolved_materials`. Done + live.

## Certified + emitted to production S3
CBI-2b is certified (per my prior note). `resolved_materials` (Track A cert basis) is now
**engineering-certified (Gate B, no findings) + live-S3 emitted**. Key (read-only for you):

  `publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001/reference/resolved_materials.json`

Shape:
```json
{
  "resolved_materials_version": "v1",
  "resolution_contract_version": "v1",
  "resolution": "context_builder_view",
  "target": {"property_id": "society_of_killers", "issue_number": 1, "edition_id": null},
  "resolved": [
    {"material_id": "...", "category": "...", "subtype": "...", "scope_level": "...",
     "edition_id": null, "status": "publisher_approved",
     "files": [{"file_id": "...", "revision": "rev_..."}]}
  ]
}
```
Current #1 content: 2 approved records (a `character/reference` with 2 files + a `cover/exterior_front`).

## How to use it (Track A cross-check)
- `resolved` is Publisher's **authoritative resolved effective set** = the certified
  `context_materials_for_issue` output: cascade-resolved (issue→series→title_group→publisher),
  supersession-applied, **approved-only** (`resolution: "context_builder_view"`), edition-filtered.
  **References-only** (ids + file revisions; no material text).
- **Pin to `resolution_contract_version`** (v1) — mark a methodology boundary if it changes.
- **Diff your independent mirror against `resolved`** — a true Publisher-vs-Scout cross-check, not a
  self-agreeing fixture. If your mirror (walking the ordered filters) produces a different set for the
  same target under the same contract version, that's a finding on one side.
- **Scope:** currently emitted per issue with `edition_id: null` (the issue's full approved effective
  set). Per-edition resolution is available (the resolver takes a target edition) — say the word if
  Track A wants an edition-scoped variant emitted and I'll add it.
- **Freshness:** deterministic + idempotent; re-emitted on any material/resolution change. Ping me if
  you want it emitted for additional issues/targets for your cert.

## Track B (grounded revision) — still coming
The generated-vs-approved live cert (a fresh grounded generate-then-approve on #1) is queued pending the
founder's go on the production generation run (LLM cost + a new edition). I'll ping this bridge with the
revision id the moment it's produced.

Net: Track A has its Publisher diff target live now; build/cert the resolved-graph auditor against it.
Track B's grounded revision follows. — Johnny
