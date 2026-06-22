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
| Weak Artifact Queue       | `reports/weak_artifacts/weak_artifact_queue.md` | Phase 1 |
| Review Priority Queue     | `reports/review_priority/review_priority_queue.md` | Phase 2 |
| Page Heat Map             | `reports/page_heatmap/page_heat_map.md`    | Phase 2 |
| Audit History             | `reports/audit_history/audit_history.md`   | Phase 2 |
| Root Cause Report         | `reports/root_cause/root_cause_report.md`  | Phase 3A |
| Highest Leverage Failure Report | `reports/highest_leverage/highest_leverage_failure_report.md` | Phase 3A |
| Failure Cluster Report    | `reports/failure_clusters/failure_cluster_report.md` | Phase 3B |
| Retrieval Blockers Report | `reports/retrieval_blockers/retrieval_blockers_report.md` | Phase 3B |
| Historical Intelligence Report | `reports/historical/historical_intelligence_report.md` | Phase 4 |
| Retrieval Readiness Intelligence Report | `reports/retrieval_readiness/retrieval_readiness_intel.md` | Phase 5 |
| Scout Daily Digest | `reports/digest/daily_digest.md` | Phase D1 |

All report types are **read-only, deterministic, and advisory**: Scout inspects, scores,
explains, and recommends; it never modifies canonical data, approves/rejects/locks
artifacts, or bypasses publisher review (Charter §4). Reports are generated without LLM,
embedding, or vision calls. Each report pairs a human-readable Markdown rendering with a
stable, machine-readable JSON block so both humans and AI engineering agents can consume it
deterministically.

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

## 5. Phase 2 — Publisher Intelligence Reports

Deterministic, read-only, advisory. Filenames are fixed (deterministic). Impact is a
qualitative band (`high|medium|low`) — never a numeric prediction. See
`docs/architecture/REVIEW_PRIORITIZATION.md` for the ranking model.

### 5.1 Review Priority Queue

Ranked advisory worklist. Ordering: severity desc → page asc (unpaged last) → effort asc →
artifact_id. JSON block:

```json
{
  "total": 0,
  "by_impact": {"high": 0, "medium": 0, "low": 0},
  "queue": [
    {"priority_rank": 1, "artifact_id": "", "page": null, "severity": "",
     "estimated_impact": "high", "effort": 0, "blocking_issues": [],
     "primary_weakness": "", "suggested_action": ""}
  ]
}
```

### 5.2 Page Heat Map

Per-page rollup of weak signals; non-page ids bucketed as `unpaged`. JSON block:

```json
{
  "pages": [
    {"page": 2, "artifact_count": 0, "weak_count": 0,
     "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
     "page_impact": "high"}
  ],
  "unpaged_count": 0
}
```

### 5.3 Audit History

Trend over recorded audit snapshots (capped at 30). Reports *measured* historical scores
and deltas (not predictions). JSON block:

```json
{
  "history": [
    {"timestamp": "", "dataset_id": "", "quality_score": 0,
     "scores": {}, "artifact_count": 0, "weak_total_flagged": 0}
  ],
  "latest_delta": {"quality_score_change": 0, "direction": "unchanged"}
}
```

## 6. Phase 3 — Dataset Failure Analysis Reports (planned)

Deterministic, read-only, **diagnostic** (not prescriptive of engineering action). These
aggregate the per-artifact `blocking_issues` already produced in Phase 1/2 into a stable
failure taxonomy, for both humans and AI engineering agents. Detailed schemas are finalized
at Phase 3A Gate B; the shapes below are indicative.

### 6.1 Root Cause Report

Aggregates failures by type with factual counts/percentages and affected artifacts/pages.

```json
{
  "dataset": "society_of_killers/issue_1",
  "artifact_count": 105,
  "failures": [
    {"failure_type": "missing_characters", "domain": "enrichment", "severity": "medium",
     "affected_count": 90, "affected_percent": 86, "affected_pages": [3, 6, 12],
     "affected_artifact_ids": ["page_3_panel_4"], "explanation": "..."}
  ]
}
```

### 6.2 Highest Leverage Failure Report

Identifies the **largest failure category** (diagnostic only — it names the dominant
failure, its scale, and a qualitative impact band, but does **not** prescribe specific
engineering actions). Impact is a qualitative band (`high|medium|low`); **no numeric
predicted score increase is ever emitted** — only measured counts and percentages.

```json
{
  "highest_leverage_failure": {
    "failure_type": "missing_characters", "domain": "enrichment",
    "affected_count": 90, "affected_percent": 86, "estimated_impact": "high",
    "rationale": "Largest failure category by coverage."
  },
  "ranked_failures": [ /* same shape, sorted */ ],
  "process_backlog": {"not_approved": 104, "unreviewed": 105}
}
```

### 6.3 Failure Cluster Report (Phase 3B)

Locates where failures concentrate: issue-wide (systemic), per-page (localized), or in the
unpaged bucket. Workflow failures are **shown and tagged** `category: "workflow"` —
separated from `content`, never hidden. Thresholds: issue-wide ≥ 80%, page cluster ≥ 50% of
a page's artifacts (min 2). See `FAILURE_ANALYSIS.md` §8.

```json
{
  "artifact_count": 105,
  "thresholds": {"issue_wide_percent": 80, "page_fraction": 0.5, "min_count": 2},
  "issue_wide_failures": [ {"failure_type","domain","category","severity","affected_count","affected_percent","estimated_impact"} ],
  "page_clusters":       [ {"page","failure_type","domain","category","affected_count","page_artifact_count","concentration_percent","severity","estimated_impact"} ],
  "unpaged_cluster":      {"artifact_count","failures":[ ... ]}
}
```

### 6.4 Retrieval Blockers Report (Phase 3B)

Assesses dataset **readiness** for grounded retrieval/QA — never performs or implements
retrieval (Charter §4). See `RETRIEVAL_READINESS.md`.

```json
{
  "retrieval_readiness_score": 25,
  "packet_coverage": {"packets_evaluated":1,"artifacts_referenced":1,"artifact_count":105,"coverage_percent":1},
  "packet_blockers":   [ {"blocker","severity","affected_packets","detail"} ],
  "artifact_blockers": [ {"blocker_type","severity","affected_count","affected_percent","estimated_impact"} ]
}
```

### 6.5 Historical Intelligence Report (Phase 4)

Deterministic trend analysis over recorded `audit_history` snapshots for the most-recent
dataset (or `?dataset_id=`). **Explains change; never predicts it.** Confidence:
`insufficient_history` (<2 snapshots), `preliminary` (2), `trend` (≥3). Reads no canonical
data. See `HISTORICAL_INTELLIGENCE.md`.

```json
{
  "dataset_id": "society_of_killers/issue_1",
  "snapshots_analyzed": 5,
  "confidence": "trend",
  "window": {"first": "...", "last": "..."},
  "metrics": [ {"name","better_when","first","last","change","direction","consistency","series":[]} ],
  "failure_trends": [ {"failure_type","domain","first_percent","last_percent","change","direction"} ],
  "new_failures": [], "resolved_failures": [],
  "stagnant_domains": [ {"domain","first_percent","last_percent","change"} ],
  "delta": {"from","to","metrics":{},"failures":{},"new_failures":[],"resolved_failures":[]},
  "observed_correlations": [ {"interval":{"from","to"},"quality_change":0,"inferred_changes":{}} ],
  "note": "Observational only ..."
}
```

### 6.6 Retrieval Readiness Intelligence Report (Phase 5)

A derived synthesis classifying retrieval readiness into four dimensions (coverage,
grounding_quality, traceability, confidence_boundaries) and a verdict
(`ready`/`partially_ready`/`not_ready`; grounding is the hard-stop). Reuses Phase 3B
Retrieval Blockers + Phase 1 retrieval block + Phase 4 trend. Assesses readiness only —
never performs retrieval; no recommendations, no predictions. See `RETRIEVAL_READINESS.md` §8.

```json
{
  "dataset_id": "society_of_killers/issue_1",
  "verdict": "not_ready",
  "readiness_score": 25,
  "dimensions": [ {"dimension","status","measured_percent","evidence","contributing_blockers"} ],
  "strengths": ["confidence_boundaries"],
  "weaknesses": ["coverage", "grounding_quality", "traceability"],
  "trend": {"retrieval_readiness": "stable", "confidence": "trend"},
  "explanation": "...", "note": "Assesses readiness only ..."
}
```

### 6.7 Scout Daily Digest (Phase D1)

A **pure projection** over the Phase 1–5 blocks — a consolidated, de-duplicated front-door
summary. **No new intelligence computation, no schema change.** Selects: headline quality
(+ delta), readiness verdict, the highest-leverage failure, today's top review items,
since-previous-audit changes, stagnant domains, and links to the deep reports. Served at
`GET /audit/digest`.

```json
{
  "dataset_id": "society_of_killers/issue_1",
  "quality_score": 53, "quality_delta": 0, "trend": {"confidence": "trend"},
  "readiness": {"verdict": "not_ready", "score": 25, "grounding_status": "weak", "weaknesses": []},
  "highest_leverage_failure": { ... },
  "review": {"total": 105, "by_impact": {}, "top_items": [ ... ]},
  "changes_since_last_audit": {"quality_change": 0, "new_failures": [], "resolved_failures": []},
  "stagnant_domains": [], "report_links": { ... }, "note": "Consolidated read-only summary ..."
}
```
### Future — Repository Intelligence Reports

These reports are not yet implemented.

They are planned for Repository Intelligence and operate on the
Edenseek Publishing Repository rather than a single dataset.

#### Repository Health Report

Location:

```text
reports/repository/repository_health.md
```

Purpose:

Assess repository-wide health.

Examples:

- missing assets
- missing metadata
- orphaned records
- invalid hierarchy placement
- incomplete issues

#### Publisher Readiness Report

Location:

```text
reports/publisher_readiness/publisher_readiness.md
```

Purpose:

Assess whether a publisher's content is ready for publication.

Examples:

- approval coverage
- metadata completeness
- retrieval readiness
- issue certification status

#### Dataset Registry Report

Location:

```text
reports/registry/dataset_registry_report.md
```

Purpose:

Summarize repository contents.

Examples:

- publishers indexed
- series indexed
- issues indexed
- approved issues
- issues awaiting review

Note:

These reports operate on repository-level information rather than
individual issue datasets and are intended for a future Repository
Intelligence phase.

## 7. Formatting Rules

- Markdown for human-facing files; JSON blocks for machine-consumed sections.
- Timestamps ISO-8601; commit SHAs short form with subject.
- Never emit secrets (enforce existing path containment; never read `.env` into a report).
