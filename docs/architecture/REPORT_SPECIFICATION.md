# Report Specification

> Output contracts for Scout's report types.
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: fdf0ab8

## 1. Report Types

| Type             | File location                  | Status |
|------------------|--------------------------------|--------|
| Strategic Report | `reports/<timestamp>.md`       | exists |
| Intake Report    | `reports/intake/<timestamp>.md`| planned (v0.4+) |

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

## 4. Formatting Rules

- Markdown for human-facing files; JSON blocks for machine-consumed sections.
- Timestamps ISO-8601; commit SHAs short form with subject.
- Never emit secrets (enforce existing path containment; never read `.env` into a report).
