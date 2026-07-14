# Dataset Input Contract — Publisher Lifecycle Audit

> The observed schema of the publisher-side repository artifacts Scout reads, organized by
> Publisher lifecycle phase. Scout is a **Publisher Lifecycle Audit Sidecar**: each phase
> emits repository artifacts; Scout reads only the permitted artifacts for that phase,
> performs phase-appropriate comparisons, and writes only Scout reports.
> Read-only: Scout never writes to these files (Charter §4). Derives from `SCOUT_CHARTER.md`
> and the Scout Data Access Contract. Last verified against commit: HEAD

## 0. Lifecycle phases and Scout-readable inputs

The Publisher lifecycle is: Comic → Intake → Processing → Metadata Generation → Human Review
→ Approved Dataset → Canonical Repository → Reader. The canonical end-to-end Publisher workflow
is defined in the Edenseek repository at `docs/architecture/publisher_workflow.mmd` (the
approved source of truth). Per the Scout Data Access Contract, the permitted Scout-readable
repository artifacts per phase are:

| Phase | Repository stage | Scout-readable inputs | Activation |
|---|---|---|---|
| Intake | `intake/` | original uploads (presence + placement metadata) | defined; staged |
| Processing | `processing/` | page images, classification, panel segments, geometry, generation outputs (structure, observation-only) | defined; staged |
| Metadata Generation | `processing/` | `metadata_drafts`, `generation_outputs`, `prompt_context_packets` (generated metadata drafts) | defined; staged |
| Human Review | `processing/`, `reference/` | `review_states`, `approval_states` (read as state summaries, never set); reference materials | defined; staged |
| **Approved Dataset** | `approved/` | `approved_dataset.json`, `approved_llm_outputs.json`, `retrieval_evidence_packets.json` | **active (§1–§6)** |
| Canonical Repository | `registry/` | `dataset_registry.json` (identity/lineage/approval-state summaries); placement metadata | defined; staged |
| Reader | — | none (Scout does not read Reader surfaces) | n/a |

Pre-approval phases are **observation-only and advisory**: Scout reads them to diagnose and
report; findings return to the Publisher workflow for human correction. Scout never approves,
gates, or mutates any phase artifact or its state. Phases are activated incrementally as each
phase's comparisons and reports are validated during the Week 11 Publisher Workflow implementation & validation (the per-phase Scout audit is its audit component).

The remainder of this document specifies the **Approved Dataset** phase schema in detail (the
phase active today). Other phases reuse the same identity and artifact shapes; their detailed
schemas are added as each phase is activated. The schema shapes below remain unchanged — only
the storage location and lifecycle phase change.

## 1. Files (Approved Dataset phase)

| File | Certified top-level shape | Element list |
|------|---------------------------|--------------|
| `approved_dataset.json` | **bare JSON list** | curated/approved artifacts |
| `approved_llm_outputs.json` | object wrapping `llm_enrichment_outputs` | full enrichment set (artifact population) |
| `retrieval_evidence_packets.json` | **bare JSON list** | evidence packets |

The certified frozen Publisher contract is **not uniformly wrapped**:
`approved_dataset.json` and `retrieval_evidence_packets.json` are bare JSON lists, while
`approved_llm_outputs.json` wraps its list under `llm_enrichment_outputs`. Scout's loader
(`audit_inputs._coerce_list`) accepts **either** shape — a bare list is used directly; a
wrapped object must carry its key as a list — so downstream scoring is shape-agnostic.

The **artifact population** Scout audits is `llm_enrichment_outputs`. `approved_dataset` is
the curated subset; artifacts present in the population but absent from it represent the
**approval backlog**.

## 2. `approved_dataset.json`

A **bare JSON list** of approved-artifact objects (no wrapper key):

```jsonc
[
  {
    "approval_state": "creator_approved",
    "artifact_id": "1::NEW::1",          // "<issue>::<status>::<n>"
    "artifact_type": "panel",            // "panel" | "spread"
    "attributes": { "action": "...", "mood": "...", "setting": "..." },
    "characters": [ /* see §5 */ ],
    "dialogue": [ /* see §5 */ ],
    "geometry": { "height", "width", "x", "y" },
    "llm_input_version": "v1",
    "metadata_review_state": "approved", // per-artifact review state (additive)
    "page_range": [1],
    "summary": "..."
  }
]
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
      "metadata_review_state": "approved",   // "unreviewed" | "reviewed" | "approved"
      "output": {
        "classification": { "tags": [ "..." ] },          // list (v1.1) OR {action,mood,setting} (v1) — see note
        "entities":       { "characters": [] },           // opaque list (see §5)
        "narrative":      { "dialogue": [], "summary": "..." }  // dialogue opaque (see §5)
      },
      "status": "complete",
      "version": "v1"
    }
  ]
}
```

**Heterogeneous `classification.tags` (certified).** Within a single frozen revision,
`classification.tags` appears in **two coexisting shapes**: a flat **list of string tags**
(enrichment `v1.1`) and a legacy **`{action, mood, setting}` object** (enrichment `v1`). Scout
scores `classification.tags` on **presence** (non-empty list *or* non-empty object), never on a
fixed sub-field set — so both certified shapes are honored without a Publisher change.

## 4. `retrieval_evidence_packets.json`

A **bare JSON list** of evidence-packet objects (no wrapper key):

```jsonc
[
  {
    "artifacts": [ { /* full artifact object, same shape as §2 */ } ],
    "confidence": null,        // float | null (null = not yet scored)
    "matched_fields": [],      // list
    "scope": ""                // string
  }
]
```

Packets have **no id field**; Scout assigns a deterministic synthetic id `packet_<index>`.

## 5. Documented Assumption — opaque `characters` and `dialogue`

Scout treats `characters` and `dialogue` (both on artifacts and on `output.entities` /
`output.narrative`) as **opaque lists** and scores **presence/non-presence only** (count > 0).
These lists were empty in the earliest observed data; in the certified Society of Killers
Issue 1 revision they are **now partially populated** (e.g. characters on 31/45 artifacts,
dialogue on 40/45), which does not change presence-scoring. Element shape is not yet relied
upon; when it stabilizes, richer scoring (consistency, OCR confidence) can be added in a
later phase. This is the only assumption Scout makes about the element shape.

## 6. Audit signal mapping (Approved Dataset phase)

| Memory sub-score (`PROJECT_MEMORY_SCHEMA.md` §2.3) | Source signal |
|---|---|
| `metadata_completeness` | per-artifact presence of `artifact_id`, a non-empty `classification.tags` (list or legacy object), and `narrative.summary` |
| `character_consistency` (interpreted as **recognition coverage**) | % of artifacts with non-empty `output.entities.characters` |
| `dialogue_completeness` (interpreted as **dialogue population coverage**) | % of artifacts with non-empty `output.narrative.dialogue` |
| `retrieval_readiness` | per packet: `confidence` set, `matched_fields` non-empty, `scope` non-empty, referenced artifacts `creator_approved` |

Additional dataset-level coverage tracked in the Dataset Quality Report: approval coverage
(`approved_dataset` vs population), review coverage (`metadata_review_state` — both
`reviewed` and `approved` count as reviewed), lock coverage (`metadata_locked`).

## 7. Repository Location & Resolution (certified "Option B")

The certified Approved Dataset is **not** three loose files under `approved/`. It is a single
**content-addressed processing revision**; the `approved/` surface holds only a mutable
pointer. Scout resolves the contract dynamically every run (`audit_s3_source.py`):

1. **GET `approved/published.json`** — the mutable pointer. It carries
   `revision_id` (a `rev_<sha256>` content hash) and `revision_key` (the full S3 key of the
   snapshot for that revision).
2. **GET `revision_key`** → `processing/workspace/<rev>/processing_snapshot.json` — the
   immutable snapshot. Its `artifacts` list embeds every issue file as
   `{ path, content_b64, sha256, size }`.
3. **Extract** the three contract files (`approved_dataset.json`, `approved_llm_outputs.json`,
   `retrieval_evidence_packets.json`) from that snapshot by `path`, base64-decoding
   `content_b64` and verifying each embedded `sha256`.
4. Optionally readable for the generated state:
   `processing/generated/<rev>/generated_snapshot.json`.

Issue location under the bucket:

```
publishers/<publisher_id>/title_groups/<title_group_id>/series/<series_id>/issues/<issue_id>/
    approved/published.json                         # mutable pointer (entry point)
    processing/workspace/<rev>/processing_snapshot.json   # immutable, content-addressed
```

Invariants Scout enforces on every read (`audit_s3_source.py`):

- **Resolve the pointer dynamically** — never pin a revision id in config; follow whatever the
  pointer names this run.
- **Version-pin each S3 read** — capture the S3 `VersionId` of the pointer and snapshot as run
  provenance so the audit records exactly which object versions it consumed.
- **Verify content integrity** — `sha256(snapshot_bytes)` must equal the pointer's
  `revision_id`; each extracted file must match its embedded `sha256`.
- **Fail loud, no fixture fallback** — an unset/unreachable source or any integrity mismatch
  raises `ScoutS3SourceError` rather than degrading.

Scout is read-only on the Publishing Repository (`GetObject` only) and enters through the
configured `approved/` surface; the `processing/` snapshot it follows is named by the
Publisher-published pointer, never guessed. Earlier-phase artifacts are read from the
corresponding stage directory for that phase (`intake/`, `processing/`, `reference/`,
`registry/`), per the Scout Data Access Contract. The schema shapes (§1–§6) remain unchanged;
only the storage/resolution model changes.
