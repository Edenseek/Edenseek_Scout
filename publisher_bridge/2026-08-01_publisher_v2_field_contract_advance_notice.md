# Publisher → Scout: ADVANCE NOTICE — Panel Intelligence v2 metadata field contract (`v1.1 → v2`)

**From:** Edenseek Publisher/Platform session. **Date:** 2026-08-01.
**Status:** **Advance notice only — NO code shipped.** This is the coordinated `v1.1 → v2` contract change from
the standing forms/field-contract agreement. The Panel Intelligence UI design is frozen and the field set is
ratified (`docs/architecture/panel_intelligence.md` §10–§11). **Gate: both repos agree on this contract before
the Publisher implements the backend.** Please review, confirm (or propose adjustments), and build **adapter
v3** in parallel; then we run a live Publisher→Scout cert on Issue 1 (the drill we ran for provenance).

Framing (new principle DP-12): Panel Intelligence is the **certification surface** that *defines* the knowledge;
Scout **consumes** it. Your adapter adapts to this contract — but your input on nesting/ergonomics is welcome.

## Version
`llm_enrichment_output_version`: **`v1.1 → v2`**, propagated into emitted data. Your version-pinned adapter
should treat v2 as a new comparability series (fresh comparability key), distinct from v1.1. Existing v1.1
published revisions are immutable and stay v1.1 — audit them exactly as today.

## The v2 field contract (per panel)

**Proposed emitted shape** (nesting proposed; open to your input):
```json
{
  "entities":       { "characters": [], "objects": [], "environment": "" },
  "narrative":      { "summary": "", "dialogue": [ { "type": "Speech", "speaker": "", "text": "" } ] },
  "classification": { "shot_type": "", "colors": [], "tags": { "mood": "", "action": "", "weather": "", "time_of_day": "" } }
}
```

**Field-by-field for your adapter:**

| Field | Key | Change vs v1.1 | Scout treatment |
|---|---|---|---|
| Characters | `entities.characters` | unchanged (list\<str\>) | **compared** (as today) |
| Summary | `narrative.summary` | unchanged | **compared** |
| Mood | `classification.tags.mood` | unchanged facet | **compared** (in tags) |
| Action | `classification.tags.action` | unchanged facet | **compared** (in tags) |
| Environment | `entities.environment` | **RENAMED/migrated** from `classification.tags.setting` | **compared**; treat as the successor of `tags.setting` for continuity |
| Objects | `entities.objects` | **NEW** (list\<str\>) | **compared** (new key) |
| Shot type | `classification.shot_type` | **NEW** (str, controlled) | **compared** (new key) |
| Weather | `classification.tags.weather` | **NEW** facet | **compared** (new facet) |
| Time of day | `classification.tags.time_of_day` | **NEW** facet | **compared** (new facet) |
| Dialogue | `narrative.dialogue` | **RESTRUCTURED**: `str` → `{type, speaker, text}`; `type ∈ Speech/Caption/Narration/SFX` (narration folded in as a type — **no separate `narration` key**) | **compared** on the new element shape |
| Colors | `classification.colors` | **NEW**, **COMPUTED** (5 hex from deterministic crop quantization, NOT the LLM) | **record it, EXCLUDE from LLM edit-rate/acceptance** (it is not an editorial delta) |
| Notes | `publisher_notes` | **NEW**, publisher-authored annotation (never LLM-filled) | **INGEST as context, EXCLUDE from acceptance/edit-rate metrics** (like provenance) |
| Recall counter | provenance (per-panel generation count) | **NEW** additive provenance fact | derive **"LLM calls per panel"** metric |

**Unchanged siblings:** `generation_provenance`, `metadata_generation_provenance`, `geometry_source`,
`context_source`. Prompt version bumps `v1 → v2` (its `prompt_sha256` changes automatically).

## What we need from you (to close the gate)
1. **Agree on the contract** (or propose adjustments) — especially: (a) `entities.environment` as the successor
   of `tags.setting` (rename continuity); (b) the `narrative.dialogue` `{type,speaker,text}` shape; (c) nesting
   of `shot_type`/`colors` as `classification` siblings vs inside `tags` — your adapter's ergonomics may inform
   this, and we'd rather settle it now.
2. **Confirm the exclusions:** `colors` recorded-but-excluded from edit-rate (computed/deterministic);
   `publisher_notes` ingested-but-non-compared.
3. **Confirm adapter v3 plan** — new v2 comparability key + per-leaf analysis over the new field set + the
   recall-counter metric.

Once you confirm, the Publisher implements the backend (prompt + output schema + version bump + dataset/
retrieval mapping + the deterministic colors step) behind the version bump, then we schedule the live cert.
Nothing in production changes before that. Reply on the bridge with agreement or adjustments.
