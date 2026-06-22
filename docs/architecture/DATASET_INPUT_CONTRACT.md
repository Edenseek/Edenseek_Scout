# Dataset Input Contract (Phase 1)

> The observed schema of the publisher-side input files Scout audits in Phase 1.
> Derived from real Edenseek data (`society_of_killers`, issue 1) and committed as
> fixtures under `fixtures/dataset/society_of_killers/issue_1/`.
> Read-only: Scout never writes to these files (Charter §4).
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: HEAD

## 1. Files

| File | Top-level wrapper key | Element list |
|------|-----------------------|--------------|
| `approved_dataset.json` | `approved_dataset` | curated/approved artifacts |
| `approved_llm_outputs.json` | `llm_enrichment_outputs` | full enrichment set (artifact population) |
| `retrieval_evidence_packets.json` | `retrieval_evidence_packets` | evidence packets |

The **artifact population** Scout audits is `llm_enrichment_outputs`. `approved_dataset` is
the curated subset; artifacts present in the population but absent from it represent the
**approval backlog**.

## 2. `approved_dataset.json`

```jsonc
{
  "approved_dataset": [
    {
      "approval_state": "creator_approved",
      "artifact_id": "1::NEW::1",          // "<issue>::<status>::<n>"
      "artifact_type": "panel",
      "attributes": { "action": "...", "mood": "...", "setting": "..." },
      "characters": [],                     // opaque list (see §5)
      "dialogue": [],                       // opaque list (see §5)
      "geometry": { "height", "width", "x", "y" },
      "llm_input_version": "v1",
      "page_range": [1],
      "summary": "..."
    }
  ],
  "approved_dataset_version": "v1"
}
```

## 3. `approved_llm_outputs.json`

```jsonc
{
  "llm_enrichment_output_version": "v1",
  "llm_enrichment_outputs": [
    {
      "artifact_id": "1::NEW::1",
      "input_ref": "1::NEW::1",
      "metadata_locked": false,
      "metadata_review_state": "unreviewed",   // e.g. "unreviewed" | "reviewed"
      "output": {
        "classification": { "tags": { "action", "mood", "setting" } },
        "entities":       { "characters": [] },           // opaque list (see §5)
        "narrative":      { "dialogue": [], "summary": "..." }  // dialogue opaque (see §5)
      },
      "status": "complete",
      "version": "v1"
    }
  ]
}
```

## 4. `retrieval_evidence_packets.json`

```jsonc
{
  "retrieval_evidence_packet_version": "v1",
  "retrieval_evidence_packets": [
    {
      "artifacts": [ { /* full artifact object, same shape as §2 */ } ],
      "confidence": null,        // float | null (null = not yet scored)
      "matched_fields": [],      // list
      "scope": ""                // string
    }
  ]
}
```

Packets have **no id field**; Scout assigns a deterministic synthetic id `packet_<index>`.

## 5. Documented Assumption — opaque `characters` and `dialogue`

In the observed data, `characters` and `dialogue` (both on artifacts and on
`output.entities` / `output.narrative`) are **empty in every record**, so their element
shape cannot be observed. For Phase 1, Scout treats them as **opaque lists** and scores
**presence/non-presence only** (count > 0). When populated data becomes available, element
shape can be inspected and richer scoring (consistency, OCR confidence) added in a later
phase. This is the only assumption Scout makes about the contract.

## 6. Audit signal mapping (Phase 1)

| Memory sub-score (`PROJECT_MEMORY_SCHEMA.md` §2.3) | Source signal |
|---|---|
| `metadata_completeness` | per-artifact presence of `artifact_id`, classification `tags.{action,mood,setting}`, `narrative.summary` |
| `character_consistency` (interpreted as **recognition coverage**) | % of artifacts with non-empty `output.entities.characters` |
| `dialogue_completeness` (interpreted as **dialogue population coverage**) | % of artifacts with non-empty `output.narrative.dialogue` |
| `retrieval_readiness` | per packet: `confidence` set, `matched_fields` non-empty, `scope` non-empty, referenced artifacts `creator_approved` |

Additional dataset-level coverage tracked in the Dataset Quality Report: approval coverage
(`approved_dataset` vs population), review coverage (`metadata_review_state`), lock coverage
(`metadata_locked`).

## Future Repository Location

In repository-backed deployments these files are expected under:

publishers/
  publisher_id/
    title_groups/
      title_group_id/
        series/
          series_id/
            issues/
              issue_id/
                approved/

The schema remains unchanged.

Only the storage location changes.