# Report Specification

> Output contracts for Scout's report types.
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: fdf0ab8

## 1. Report Types

| Type                      | File location                              | Status |
|---------------------------|--------------------------------------------|--------|
| Strategic Report          | `reports/<timestamp>.md`                   | exists |
| Intake Report             | `reports/intake/<timestamp>.md`            | planned |
| Dataset Quality Report    | `reports/dataset/<timestamp>.md`           | planned (Phase 1) |
| Character Analysis Report | `reports/character/<timestamp>.md`         | planned (Phase 1) |
| Dialogue Analysis Report  | `reports/dialogue/<timestamp>.md`          | planned (Phase 1) |
| Retrieval Readiness Report| `reports/retrieval/<timestamp>.md`         | planned (Phase 1) |
| Weak Artifact Queue       | `reports/weak_artifacts/<timestamp>.md`    | planned (Phase 1) |

The Phase 1 report types below derive from `SCOUT_CHARTER.md` §6. All are **read-only and
advisory**: Scout inspects, scores, and recommends; it never modifies canonical publisher
data, approves metadata, or bypasses publisher review (Charter §4). Each report pairs a
human-readable Markdown rendering with a machine-readable JSON block so findings can feed
memory and downstream tooling deterministically.

## 2. Strategic Report (existing + v0.4 extension)

Narrative section is unchanged (status, watching, why it matters, action, opportunity,
risk; <700 words). v0.4 adds a machine-readable block the extractor consumes:

```json
{
  "projects": {
    "edenseek": { "themes": [], "opportunities": [], "risks": [] },
    "phrasmos": { "themes": [], "opportunities": [], "risks": [] },
    "caelaris": { "themes": [], "opportunities": [], "risks": [] }
  }
}
```

Produced via structured/JSON output so memory extraction is deterministic, not regex over
prose.

## 3. Intake Report (new — continuity briefing)

The Intake Report is Scout's session-opening handoff. It is **read-only and advisory**:
every actionable line is a suggestion for a human/agent, never an instruction Scout
executes (Charter §4). Required sections:

```markdown
# Scout Intake Report — <timestamp>

## Current Branch
<git branch>

## Current Commit
<short sha> — <subject line>

## Current Milestone
<from roadmap / project.active_milestone: e.g. "Beta / Memory v0.4">

## Schedule Position
last run, next scheduled, runs today (see SCOUT_SCHEDULE.md §3)

## Recent Changes
<git log --oneline since last intake; diff --stat summary>

## Known Risks
<from memory.projects.*.risks + open critical issues>

## Architecture Warnings
<from architecture-compliance check: doc/code drift, deprecated hooks,
 missing job store, hardcoded schedule, commit vs. last_verified_commit, etc.>

## Recommended Tasks
<derived from project.next_action + risks + warnings + milestone; advisory only>

## Questions for Claude
<routed from project.open_questions: implementation, codebase, reliability, architecture>

## Questions for ChatGPT
<routed from project.open_questions: strategy, research, market, content>
```

### 3.1 Field sourcing

| Section               | Source (all read-only) |
|-----------------------|------------------------|
| Current Branch/Commit | git rev-parse / log |
| Current Milestone     | `projects.*.active_milestone` / roadmap |
| Schedule Position     | scheduler state + memory |
| Recent Changes        | git log / diff --stat |
| Known Risks           | `projects.*.risks` |
| Architecture Warnings | compliance check vs. baseline + `last_verified_commit` |
| Recommended Tasks     | `projects.*.next_action` + risks + warnings + milestone |
| Questions for Claude  | `projects.*.open_questions`, routed by topic (build/code/reliability) |
| Questions for ChatGPT | `projects.*.open_questions`, routed by topic (strategy/research/market) |

## 4. Phase 1 — Dataset Intelligence Reports

These reports are produced from **read-only** inspection of publisher-side artifacts
(`approved_dataset.json`, `approved_llm_outputs.json`, `retrieval_evidence_packets.json`,
reference materials, character sheets, scripts, creator notes). Inputs are never modified.
Outputs are written only to Scout's own `reports/` tree and memory.

Common conventions for all Phase 1 reports:

- Every finding references the source artifact (id/path) and a timestamp.
- Quality scores are deterministic and repeatable for the same input (Charter §5).
- Every report carries a machine-readable JSON block alongside the Markdown narrative.
- Severity uses a fixed scale: `critical | high | medium | low | info`.

### 4.1 Dataset Quality Report

Audits overall dataset and metadata completeness/health.

```markdown
# Dataset Quality Report — <timestamp>

## Summary
<dataset id/path · artifact count · overall quality_score (0–100)>

## Metadata Completeness
<required fields present vs. missing, by artifact category>

## Findings
<list: artifact id · issue · severity · recommendation>

## Recommendations
<advisory improvement proposals for human review>
```

```json
{
  "dataset": "<id|path>",
  "artifact_count": 0,
  "quality_score": null,
  "completeness": { "present": 0, "missing": 0, "fields_missing": [] },
  "findings": [
    { "artifact_id": "", "issue": "", "severity": "", "recommendation": "" }
  ]
}
```

### 4.2 Character Analysis Report

Evaluates character recognition and cross-issue consistency against reference materials
(character sheets).

```markdown
# Character Analysis Report — <timestamp>

## Summary
<characters covered · consistency_score (0–100)>

## Per-Character Findings
<character · appearances · recognition issues · consistency conflicts · severity>

## Reference Utilization
<which character sheets were available vs. unused>

## Recommendations
<advisory>
```

```json
{
  "consistency_score": null,
  "characters": [
    { "name": "", "appearances": 0, "recognition_issues": [], "conflicts": [], "severity": "" }
  ],
  "reference_materials": { "available": [], "unused": [] }
}
```

### 4.3 Dialogue Analysis Report

Evaluates dialogue-extraction quality and completeness (e.g. OCR quality where applicable).

```markdown
# Dialogue Analysis Report — <timestamp>

## Summary
<artifacts covered · dialogue_completeness_score (0–100)>

## Findings
<artifact · missing/garbled/low-confidence dialogue · severity>

## Recommendations
<advisory>
```

```json
{
  "dialogue_completeness_score": null,
  "findings": [
    { "artifact_id": "", "issue": "", "confidence": null, "severity": "", "recommendation": "" }
  ]
}
```

### 4.4 Retrieval Readiness Report

Assesses how ready artifacts are for retrieval, based on the evidence packets. Scout
**assesses readiness only** — it never performs, implements, or alters retrieval (Charter
§4).

```markdown
# Retrieval Readiness Report — <timestamp>

## Summary
<packets evaluated · retrieval_readiness_score (0–100)>

## Findings
<packet/artifact · gap (missing evidence, weak grounding, coverage) · severity>

## Recommendations
<advisory — improvements for human review, not retrieval changes>
```

```json
{
  "retrieval_readiness_score": null,
  "findings": [
    { "packet_id": "", "gap": "", "severity": "", "recommendation": "" }
  ]
}
```

### 4.5 Weak Artifact Queue

A prioritized queue of artifacts that fall below quality thresholds and warrant human
attention. This is an advisory worklist, never an instruction Scout executes.

```markdown
# Weak Artifact Queue — <timestamp>

## Summary
<total flagged · by severity>

## Queue
<ranked: artifact id · score · primary weakness · severity · suggested action>
```

```json
{
  "total_flagged": 0,
  "queue": [
    { "artifact_id": "", "score": null, "weakness": "", "severity": "", "suggested_action": "" }
  ]
}
```

## 5. Formatting Rules

- Markdown for human-facing files; JSON blocks for machine-consumed sections.
- Timestamps ISO-8601; commit SHAs short form with subject.
- Never emit secrets (enforce existing path containment; never read `.env` into a report).
