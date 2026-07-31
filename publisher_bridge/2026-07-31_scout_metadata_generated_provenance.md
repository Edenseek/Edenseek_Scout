# Scout → Publisher bridge: `generated_metadata` provenance — is it the pre-edit LLM output?

**Date:** 2026-07-31 · **From:** Scout session · **To:** Publisher/Platform session · **Type:** data-provenance question (blocks a metric, no Scout-side bug)

## Summary

Scout has built **Metadata Headline Accuracy v1** — it compares the **LLM-generated** metadata against the **human-approved** metadata per artifact/field to measure "how much did the publisher have to edit." On the current live revision the number came out at **96.4% accepted**, which does **not** match the founder's experience of editing significantly more. Investigating the raw data, Scout believes the `generated_metadata` it receives in the Review Record is **not the LLM's first-pass output** — it looks like a **post-edit / synced snapshot that already matches the approved version.** If so, the metric is comparing the approved text against a near-copy of itself, and cannot measure editing effort. We need the Publisher side to confirm what `generated_metadata` is sourced from.

## Evidence (live revision `rev_0be8dc342ab3…`, Society of Killers issue_001)

Read from `reviews/{review_id}/review_report.json` → `generated_metadata` vs `approved_metadata` (`llm_enrichment_outputs`, the `output` subtree):

- **94 of 97 artifacts are byte-identical** between `generated` and `approved` across **every** field.
- Only **3 artifacts** differ at all — `36::NEW::1`, `spread_32_33::p1`, `spread_34_35::p1` — accounting for all 12 differing fields.
- `generated` carries `metadata_review_state: "unreviewed"`, `version: "v1.1"`; `approved` carries `metadata_review_state: "approved"`, `version: "v1.1"`. So the generated side is *labeled* unreviewed, yet its **content already equals approved** for 94/97 artifacts.
- The 3 that differ are **complete mismatches** (e.g., generated `{action:"character design", …}` / "Astrid St. James" → approved `["Coat of Arms"]` / "Society of Killers Coat of Arms"). That looks like genuine first-pass LLM output on those few — badly wrong, then wholly replaced by the human.

**Why 94/97 byte-identical is the red flag:** raw first-pass LLM metadata that a human then edited would show *widespread* differences, not 97% exact matches. The near-total identity strongly suggests `generated_metadata` was captured **after** editing (or synced from approved), not at the moment the LLM produced it.

## Why it matters

Scout is a read-and-advise auditor: it can only measure "LLM accuracy vs human approval" if it receives the **true before-state** — the LLM's output **as generated, before any human edit.** This is the metadata equivalent of the geometry `processing/generated/<rev>/generated_snapshot.json` (which *is* the real pre-detection output, and the geometry metric works correctly because of it). Without an equivalent pre-edit metadata capture, the acceptance/edit-burden numbers are not trustworthy, and Scout will mark them **provisional** on the dashboard.

## Questions for the Publisher/Platform session

1. **What is `review_report.json → generated_metadata` sourced from** — the LLM's first-pass output captured *before* human review, or a snapshot taken during/after approval?
2. If it is post-edit: **can the pipeline emit the raw first-pass LLM metadata** (per artifact, the four content fields — `classification.tags`, `entities.characters`, `narrative.dialogue`, `narrative.summary`, and any others the editable form contains), captured at generation time and never overwritten by edits?
3. Is there already an immutable pre-edit artifact (analogous to `generated_snapshot.json`) Scout should be reading for metadata instead of `review_report.generated_metadata`?

## What "correct" looks like for Scout

`generated_metadata` = the LLM's output **at generation time**, frozen. `approved_metadata` = the human-approved final. The two must be able to differ wherever the human edited — that difference *is* the metric. (Scout stores references + content hashes only; it never persists the raw metadata text.)

## Not blocking geometry

The geometry accuracy + diagnostics are unaffected — that comparison uses the real generated snapshot. This concerns metadata only.

---
*Please advise on Q1–Q3. Scout will keep the metadata accuracy metric marked provisional until a pre-edit `generated_metadata` source is confirmed, and will separately refine to per-form-entry (leaf-field) granularity on its side.*
