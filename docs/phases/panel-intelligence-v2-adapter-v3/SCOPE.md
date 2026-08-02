# Scope — Adapter v3 (Panel Intelligence v2 field contract `llm_enrichment_output_version v1.1 → v2`)

**Status:** SCOPED · gate CLEARED (Publisher confirmed all items 2026-08-01,
`publisher_bridge/2026-08-01_publisher_v2_contract_confirmed_go_build_adapter_v3.md`) · ready to build.
**Discipline:** certified-first — build → 2 adversarial rounds → cert write-up → deploy → live cert, each
separate. Additive; existing v1.1 revisions stay immutable and audit unchanged.

## 1. Objective
Consume the Publisher's v2 metadata field contract: a larger, restructured field set, with **per-leaf-field**
acceptance/edit analysis (the deferred granularity refactor lands here), structured-`dialogue` comparison,
explicit exclusion of non-editorial fields, and an "LLM calls per panel" metric. v2 forms a new comparability
series distinct from v1.1.

## 2. The v2 field set

**Compared (LLM-editorial) — the per-leaf denominator:**

| Leaf key | Type | vs v1.1 |
|---|---|---|
| `entities.characters` | list<str> | unchanged |
| `entities.objects` | list<str> | NEW |
| `entities.environment` | str | RENAMED from `classification.tags.setting` (labeled boundary, not spliced) |
| `narrative.summary` | str | unchanged |
| `narrative.dialogue` | list<{type,speaker,text}> | RESTRUCTURED from str; structured-element comparison |
| `classification.shot_type` | str (controlled) | NEW |
| `classification.tags.mood` | str | unchanged facet (now its own leaf) |
| `classification.tags.action` | str | unchanged facet (now its own leaf) |
| `classification.tags.weather` | str | NEW facet |
| `classification.tags.time_of_day` | str | NEW facet |

**Recorded but EXCLUDED from acceptance/edit-rate:**
- `classification.colors` — computed (deterministic crop quantization), not LLM → would always read "accepted"
  and inflate; record hash only.
- `publisher_notes` — human-authored, not LLM → ingest as context, hash only, never compared. **Raw text never
  persisted** (governance).

Exclusion is by a **Publisher-emitted record-level `field_sources` map** (CONFIRMED). Keys are full paths,
e.g. `{"output.classification.colors": "computed", "publisher_notes": "publisher"}`; any field **not** listed
defaults to `"llm"`. Scout excludes every leaf whose source `!= "llm"` from the compared/acceptance set —
deterministic and future-proof (a new computed field just adds an entry). Note the key format: output leaves
are prefixed `output.` (map `output.<leaf>` ↔ Scout's `<leaf>` key); `publisher_notes` is a record-level
sibling (no prefix).

**Unchanged siblings:** `generation_provenance`, `metadata_generation_provenance` (v2 acceptance/fresh logic is
untouched — carries over as-is), `geometry_source`, `context_source`. Prompt `v1 → v2` (sha256 changes).

## 3. Module changes

- **`review_contract_adapter.py`**
  - `_extract_content_fields` → **version-aware**: v1.1 keeps the current 4-field extraction; v2 extracts the
    10 compared leaves above. Decompose `classification.tags` dict into per-facet leaves; map
    `entities.environment` as the `setting` successor within v2.
  - Carry the **excluded** fields (colors/publisher_notes) into a separate `non_editorial` map (hash-only) so
    they're recorded but never enter the compared set. Honor the `source` marker when present.
  - `_normalize_metadata`: version-pin — accept `v1.1` and `v2`; fail-fast on unknown (as today). Keep the
    per-output provenance + disposition carry-through unchanged.
  - Recall-counter: surface the per-panel generation count from provenance for the new metric.
- **`delta_metadata_revision.py`**
  - `FIELDS` becomes **version-parameterized** (v1.1 = current 4; v2 = the 10 leaves). Per-leaf tallies /
    per-field aggregates already generalize — they key on the field list.
  - `dialogue` comparison: extend `_canon`/`_elements`/`_measures` to render `{type,speaker,text}` elements
    (element-set + order); an edit = element change / add / remove / reorder. Keep set-Jaccard for the
    list-of-dicts shape; token-Jaccard fallback for text leaves.
  - **Version bumps that reflect real methodology changes:** `METADATA_REVISION_DISTANCE_VERSION v1 → v2`
    (field set + dialogue distance changed) and `METADATA_ACCURACY_VERSION v2 → v3` (per-leaf denominator).
    Both must land in the comparability axis AND `scout_delta_audit.static_versions()` fingerprint (the
    dual-condition lesson). The Publisher `metadata_schema_version v1.1→v2` moves the axis automatically too.
  - New metric: `llm_calls_per_panel` from the recall counter (additive; provenance-derived).
- **`scout_report_index.py`** — no new axis needed beyond what already flows (`metadata_schema_version`,
  `metadata_accuracy_version`, `metadata_revision_distance_version` all already axes). Verify the v2 keys
  render.
- **`scout_delta_audit.py`** — add the bumped versions to `static_versions()`.
- **Dashboard** — the per-leaf editorial-burden table now shows the finer field set (this is the "per-form-
  entry" view the founder asked for). Colors/notes shown as recorded-but-excluded. (Joint UI review.)
- **Tests** — v2 fixtures (a v2 review record); per-leaf acceptance; dialogue structured edits (add/remove/
  reorder/speaker-change); colors/notes excluded from denominator; marker-based vs list-based exclusion;
  v1.1 still audits identically (backward compat); version bumps land in axis + fingerprint; recall metric.

## 4. Design decisions (locked unless Publisher adjusts)
1. **Per-leaf identity:** one leaf per editable facet; `tags` decomposed to mood/action/weather/time_of_day.
2. **Dialogue:** one leaf, structured-element comparison (no per-line sub-leaves — lines lack stable identity).
3. **Exclusion:** by `source` marker if emitted; else versioned explicit list for v2.
4. **environment←setting:** compared v2 leaf; labeled methodology boundary, never spliced to v1.1.
5. **colors/publisher_notes:** recorded (hash only), excluded from acceptance/edit-rate.
6. **Backward compat:** v1.1 extraction + metric unchanged; v2 is a distinct series.

## 5. Publisher-confirmed inputs (2026-08-01 — gate cleared)
- **Exclusion:** record-level `field_sources` map, default `"llm"`, exclude `source != "llm"` (§2).
- **Recall counter:** `generation_provenance.generation_count` (int; 1 first generate, +1 per recall). **Ships
  LATER with the recall endpoint — off the v2 critical path.** So the `llm_calls_per_panel` metric is
  **best-effort**: read it when present, degrade gracefully (metric absent) when the field isn't emitted yet.
  The path is fixed now so v3 reads it the moment it appears.
- **`shot_type` vocab v1** (`shot_type_vocab: v1`, extensible, `"other"` fallback): `establishing · wide ·
  full · medium · close-up · extreme close-up · over-the-shoulder · point-of-view · high-angle · low-angle ·
  insert`. Compared as a normal leaf; out-of-vocab values labeled against this set (labeling only, not a gate).
- **`field_sources` + `publisher_notes` are record-level siblings of `output`** (like `generation_provenance`)
  — read at the output-entry level, not inside `output.*`.

## 6. Certified-first sequence
Build behind the version bump → 2 adversarial review rounds → cert report → merge → deploy → live cert on
Issue 1 (same drill as provenance) → jointly mark v2 stable. Nothing in production changes until the live cert.
