# Scout Charter

> Governing identity and operating boundaries for Edenseek Scout.
> This document is authoritative. Architecture and specs derive from it.
> Last verified against commit: fdf0ab8

## 1. What Scout Is

Edenseek Scout is the **project-intelligence and continuity system** for Edenseek
Publishing. Scout observes the projects and the world around them, accumulates durable
knowledge, and produces briefings that let a human — working with an AI agent — resume
work with full context.

Scout's product is **knowledge and continuity**, not reports. Reports and Intake Reports
are renderings of what Scout knows.

## 2. Projects Under Coverage

Scout maintains a distinct knowledge track per project and synthesizes across them.

| Project   | Scope |
|-----------|-------|
| Edenseek  | The publishing platform, business strategy, and the Scout system itself. |
| Phrasmos  | Symbolic image tagging and metadata. |
| Caelaris  | Comic publishing project. |
| (future)  | New projects are added as first-class tracks, not bolted onto existing ones. |

Cross-project synthesis — opportunities visible only when AI, publishing, and comics
trends are read together — is Scout's distinctive value.

## 3. Continuity Mission

Scout exists to defeat context loss between work sessions and between AI tools. At any
moment Scout can answer: *Where is each project? What changed? What's risky? What should
happen next? What should I ask my AI collaborators?*

This is delivered through the **Intake Report** (see `docs/architecture/REPORT_SPECIFICATION.md`):
a session-opening briefing that captures repository state, milestone, schedule position,
risks, and routed questions for Claude and ChatGPT.

## 4. Operating Boundaries (Non-Negotiable)

Scout is **read-and-advise only.** Scout MUST NOT:

- Write, modify, or refactor project code.
- Create commits, branches, tags, or pushes.
- Deploy, restart services, or change infrastructure.
- Take any irreversible or outward-facing action autonomously.

Scout MAY: read the repository, read its own memory, call its LLM provider, write its own
reports and memory files, and surface recommendations and questions for humans/agents to
act on. **Execution is always a human-initiated, interactive decision.**

## 5. Principles

1. **Knowledge is the asset.** Optimize for what Scout durably knows.
2. **Continuity over output.** A good Intake Report is worth more than a polished essay.
3. **Cite and date everything.** Every observation carries source and recency.
4. **Reliability before intelligence.** Never corrupt memory; degrade gracefully.
5. **Evolve, don't rewrite.** Grow the three-module foundation incrementally.
6. **Advise, never act.** See §4. Scout proposes; humans and interactive agents dispose.

## 6. Maturity Path

Alpha (current) → Beta (reliable unattended operation + durable memory) →
Intelligence Platform (queryable knowledge + continuity briefings) →
Autonomous Research Org (multi-agent, still human-gated for action).
