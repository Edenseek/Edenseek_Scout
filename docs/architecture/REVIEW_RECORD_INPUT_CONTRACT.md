# Review Record Input Contract — Scout Synchronization Audit (6.3)

> The Scout-side, **versioned** description of the Publisher-emitted artifacts the Scout
> generated-vs-approved delta consumes. Scout is an **independent, read-only, advisory
> consumer**: the Publisher PRODUCES certified artifacts; Scout CONSUMES + VERIFIES across the
> repository boundary and writes only to `edenseek-scout`. This contract is consumed through a
> single **anti-corruption boundary** (`review_contract_adapter.py`) — no Publisher shape
> leaks past it. Derives from `SCOUT_CHARTER.md`, `SCOUT_APPROVAL_DELTA_ARCHITECTURE.md`, and
> the Publisher handoff `Edenseek/docs/handoff/week11_6_3_scout_handoff.md`.

## 0. Fail-fast versioning (non-negotiable)

Scout pins the Publisher contract versions it understands:

| Artifact | Version field | Supported |
|---|---|---|
| C — Review Record | `review_report_version` | `v1` |
| D — Platform Approval | `platform_approval_version` | `v1` |
| B — Generated PAL | `generated_snapshot_version` | `v1` |

If any version is not supported, or a required field is missing/malformed, the adapter raises
`ReviewContractError` **at the boundary** — Scout never silently reinterprets an unknown
contract. When the Publisher bumps a contract version, this document and
`review_contract_adapter.py` are updated together, in one place.

## 1. Artifacts consumed (emitted by the Publisher)

| # | Artifact | Canonical key | Scout read scope |
|---|---|---|---|
| A | Approved Dataset (3 files) | `approved/published.json` → `processing/workspace/<rev>/processing_snapshot.json` | already granted (`approved/`, `processing/`) |
| B | Generated PAL | `processing/generated/<gen_rev>/generated_snapshot.json` | already granted (`processing/`) |
| C | **Review Record** | `reviews/{review_id}/review_report.json` | **needs `reviews/` read grant** (Phase B; §6 / `proposed_reviews_read_grant.md`) |
| D | **Platform Approval** | `reviews/{review_id}/platform_approval.json` | **needs `reviews/` read grant** |

- `review_id = "rev_" + published_revision_id.split("_",1)[1][:12]` (12 hex chars of the published revision's sha256).
- `<gen_rev> = "rev_" + sha256(generated_snapshot_bytes)` (full 64 hex) — content-addressed, immutable.

## 2. C — Review Record (`review_report.json`, `review_report_version: v1`)

```jsonc
{
  "review_report_version": "v1",
  "issue_identity": { "publisher_id", "title_group_id", "series_id", "issue_id" },
  "review_id": "rev_<12hex>",
  "generated_geometry": { /* B's generated_panel_geometry, or null (manual) */ },
  "generated_metadata": { /* B's generated_metadata, or null (manual) */ },
  "approved_geometry":  { "<artifact_id>": { "x","y","width","height","approved?","deleted?","isNew?" } },
  "approved_metadata":  { "llm_enrichment_output_version", "llm_enrichment_outputs": [ { "artifact_id", ... } ] },
  "provenance": {
    "published_revision_id": "rev_<sha256>",
    "generated_vs_approved": { "state": "generated_publication", "generated_snapshot_revision_id": "<gen_rev>" }
                              /* OR the string "not_applicable_manual_publication" */
  }
}
```

**The LINK** (`provenance.generated_vs_approved`) is the ONLY authoritative binding of a
publication to its Generated PAL. A **manual** publication carries the string
`"not_applicable_manual_publication"` with `generated_geometry`/`generated_metadata` both
`null` — Scout treats these as **not-applicable**, never a zero-delta.

## 3. D — Platform Approval (`platform_approval.json`, `platform_approval_version: v1`)

```jsonc
{
  "platform_approval_version": "v1",
  "review_id", "published_revision_id",
  "canonical_dataset_state": "edenseek_approved",
  "state_transition": ["creator_approved","edenseek_approved"],
  "platform_authority": { "actor", "approved_at" },
  "readiness": { "readiness_version","geometry_artifact_count","metadata_artifact_count",
                 "hard_failures","warnings","passes_integrity" },
  "certifies_review_report_key": ".../reviews/{review_id}/review_report.json"
}
```

**Canonical state machine:** `draft → creator_approved → edenseek_approved → available`. D is
written only at `edenseek_approved`. **Absence of D ⇒ `creator_approved`** (published, not yet
platform-approved); `draft` when nothing is published. `readiness` is the **Publisher/Platform's
own certified structural attestation** — Scout **reports it verbatim** (as
`publisher_certified_state`) and never re-derives, gates, or second-guesses it.

## 4. B — Generated PAL (`generated_snapshot.json`, `generated_snapshot_version: v1`)

`{ generated_snapshot_version, pal_state:"generated", generated_metadata, generated_panel_geometry }`.
`generated_metadata` is the same `{llm_enrichment_output_version, llm_enrichment_outputs:[...]}`
object as approved metadata; `generated_panel_geometry` is the auto panel dataset (§5).

## 5. Geometry — THREE representations, all normalized to one canonical shape

Verified against real emitted bytes (Publisher, 2026-07-27). All are normalized to Scout's
canonical `{ artifact_id: {bbox:(x,y,w,h), page_number, coordinate_space, flags, page_range} }`
where **`bbox` is normalized 0..1 `(x, y, width, height)`**:

- **generated** — `generated_panel_geometry` is a 6-key summary object whose `panels[]` is a flat
  list keyed by `panel_key`. Each row carries **`bbox` = PIXELS `[x1,y1,x2,y2]` corners** (kept only
  as provenance) **and `bounds` = normalized 0..1 `{x,y,width,height}`**. The adapter normalizes
  from **`bounds`** (fail-fast if absent) — never `bbox`.
- **approved page panel** — normalized 0..1 `{x,y,width,height}` (+ `deleted`/`isNew`).
- **approved spread panel** — `isSpreadPanel: true`, with page `x/y/width/height` **degenerate
  (0.01)/absent**; real geometry in **`stage_geometry`** (spread-canvas space) + `page_range`. The
  adapter uses `stage_geometry`, flags `is_spread`. Spreads are drawn → no generated counterpart →
  always **approved-only / missing panels**; the geometry delta never IoU-matches them. Spreads
  appear in **two key forms**, both carrying `isSpreadPanel` + `stage_geometry` and handled
  identically: a `spread_<pages>::pN` entry (no page `x/y/w/h`, only `stage_geometry`) and a
  `<page>::NEW::N` drawn-on-spread entry (degenerate page coords + `stage_geometry`).

**Structural sibling keys (skipped).** `approved_geometry` is an `artifact_id`-keyed map that also
carries **non-panel structural siblings** — `panel_order` (a page→artifact-id ordering dict) and
`spread_artifacts` (a collection list). The adapter **skips the known structural keys**
(`APPROVED_GEOMETRY_STRUCTURAL_KEYS`) and **fails fast on any other non-artifact member** (a member
that is neither a page geometry nor a spread) rather than reinterpreting it. Verified against
production `rev_a8c65a83a196` (Society of Killers Issue 1: 97 artifact entries = 36 page + 48 NEW +
13 spread, plus the 2 structural keys).

**Identity spaces align:** generated `panel_key` == approved `artifact_id`.

**Metadata content is nested** under `output`, `artifact_id`-keyed on both sides. Scout compares
exactly **four content fields**: `output.classification.tags`, `output.entities.characters`,
`output.narrative.dialogue`, `output.narrative.summary`.

Field shapes (Publisher census over 97 artifacts, 2026-07-27):

| field | shape |
|---|---|
| `classification.tags` | normally a `{action,mood,setting}` **dict** on **both** sides (94–95/97); **rarely a flat `list<str>`** (1/97 — a human edit); may be **`null`** (2/97) |
| `entities.characters` | `list<str>` on both sides (may be `null`) |
| `narrative.dialogue` | `list` on both sides (may be `null`) |
| `narrative.summary` | `str` |

`tags` is taken **as-is** (no shape assumption): Scout's value-equality classifies dict==dict as an
*accept*, dict-vs-list (or any change) as an *edit*, and `null`==`null` as a no-op (neither accept
nor edit). **Excluded as provenance:** `context_source`, `geometry_source`. **Excluded as
plumbing:** `artifact_id`, `input_ref`, `version`, `metadata_locked`, `metadata_review_state`,
`status`.

**Comparability is schema-version scoped** (per `SCOUT_APPROVAL_DELTA_ARCHITECTURE.md`): metadata is
compared only within a single `llm_enrichment_output_version`; artifacts whose generated vs approved
schema versions differ are reported as `schema_version_mismatch` and **excluded** from the field
aggregates — never silently mixed. **Live observation (production `rev_a8c65a83a196`, 2026-07-27):**
the generated enrichment set is `v1.1` while the approved set is `v1`, so **all 97 artifacts are a
schema-version mismatch and the metadata field delta abstains** (0 compared). This is Scout behaving
correctly (it will not compare across a declared schema boundary); whether the `v1.1`→`v1` skew is
expected — and whether the two versions are content-comparable — is a **Publisher-side question**
Scout surfaces, not one it resolves by relaxing comparability.

## 6. Scout invariants (must hold; enforced downstream)

- **Read-only / advisory.** Scout writes only to `edenseek-scout`; never any `edenseek-publishing`
  surface. Scout reports canonical state; it never sets, gates, or approves.
- **Deterministic / offline.** Deltas are geometry overlap + structural field diffs — no LLM,
  vision, or network. Reproducible from the frozen, content-addressed inputs.
- **Manual & absence-of-D are first-class** (not-applicable; `creator_approved`), never coerced
  to zero-delta or `edenseek_approved`.
- **Publisher certification stays the Publisher's.** `publisher_certified_state` (D's state +
  readiness) is carried verbatim and kept separate from Scout's independent delta.

## 7. Phase gating

- **Phase A (this contract, offline):** the adapter + delta engines operate on parsed dicts;
  no `reviews/` access needed. Unit-certified with fixtures mirroring the shapes above.
- **Phase B (after the Publisher provisions the `reviews/` read grant):** wire the `reviews/`
  S3 reader (extending `audit_s3_source`) and live-certify against the real Review Record +
  Platform Approval. See `proposed_reviews_read_grant.md`.
