# Retrieval Readiness Blockers (Phase 3B)

> The deterministic model behind the Retrieval Blockers Report.
> Derives from `SCOUT_CHARTER.md`. **Assesses readiness only — Scout never performs,
> implements, or alters retrieval, and is never a retrieval engine (Charter §4).**
> Pure: no I/O beyond loading inputs, no network, no LLM, no embeddings, no vision.

## 1. Purpose

Identify what in the *dataset* prevents reliable grounded retrieval / QA, so humans and AI
engineering agents can improve readiness. It evaluates the dataset; it does not build or run
retrieval, and it produces no reader-facing answers.

## 2. Inputs

`audit_scoring` per-artifact assessments (`summary_length`, `has_characters`,
`has_dialogue`, `page`, `missing_fields`) and the retrieval block
(`retrieval_readiness_score`, `packets_evaluated`, `artifacts_referenced`, `findings`). No
new inputs.

## 3. Packet coverage

`coverage_percent = round(100 * artifacts_referenced / artifact_count)`. Low coverage means
most artifacts have no evidence packet at all — the dominant readiness blocker when evidence
is sparse (e.g. 1 of 105 → 1%).

## 4. Packet blockers

Aggregated from the retrieval block findings (null confidence, empty `matched_fields`,
empty `scope`, unapproved referenced artifacts), plus a `low_packet_coverage` blocker when
coverage < 100% (severity `high` below 50%, else `medium`).

## 5. Artifact blockers (authored)

| blocker_type | severity | condition |
|---|---|---|
| `no_grounding` | high | summary empty (`summary_length == 0`) |
| `thin_description` | medium | `0 < summary_length < 40` chars |
| `missing_characters` | medium | no recognized characters |
| `missing_dialogue` | medium | no dialogue populated |
| `missing_page_linkage` | medium | no page derivable from `artifact_id` |
| `thin_metadata` | low | missing classification tags |

Each reports `affected_count`, `affected_percent`, `severity`, and a coverage-based
`estimated_impact` band (high ≥ 50%, medium ≥ 20%, low otherwise). **No numeric predicted
score change is emitted.**

## 6. Relationship to other reports

These blockers re-frame the same underlying dataset deficiencies through a *retrieval*
lens; counts reconcile with the Root Cause taxonomy (a regression test asserts this). Deep
packet-level / query-coverage analysis is a later phase (charter Phase 5); Phase 3B assesses
readiness only.

## 7. Guarantees

- Deterministic, read-only, diagnostic; no actions, no retrieval, no numeric predictions,
  no self-modification.
