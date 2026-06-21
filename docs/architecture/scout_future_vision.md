# Edenseek Scout — Future Vision & System Direction

> **Audience:** Future AI agents and developers onboarding to the Edenseek Scout codebase.
> **Status:** Forward-looking design document. Describes the intended long-term system, not the
> current v0.3 implementation. For current state, see
> [`scout_v0.3_synopsis.md`](./scout_v0.3_synopsis.md).
> **Owner:** Edenseek Publishing (Derek Uskert)

---

## 1. Purpose of This Document

Edenseek Scout today is a small, scheduled report generator (v0.3). This document exists to make the
*destination* explicit so that every incremental change moves Scout toward a coherent end state
rather than accreting features. If you are an agent or developer picking up work, read the v0.3
synopsis for what exists, then read this for where it is going. Every roadmap item should be
justifiable as a step toward the system described here.

---

## 2. The Long-Term Vision

**Scout will become Edenseek's autonomous intelligence and research system** — a persistent agent
that continuously observes the external world, builds and maintains durable institutional knowledge,
and produces strategic guidance on demand and on schedule.

The aspiration is a shift in kind, not degree:

| From (v0.3) | To (vision) |
|---|---|
| Writes a fresh report from a static prompt | Maintains an evolving model of the domains it tracks |
| Memory holds only a counter and timestamp | Memory is a structured, deduplicated knowledge base |
| Single LLM call per run | Multi-step research: gather → analyze → verify → synthesize |
| One scheduled daily report | Continuous monitoring with event- and schedule-driven outputs |
| Read-only Markdown dashboard | Conversational interface over accumulated knowledge |
| Reports are the product | Knowledge is the product; reports are one view of it |

The success condition, in the words of the project's own execution brief: *"Scout no longer merely
writes reports. Scout begins building institutional knowledge."*

---

## 3. Domains of Coverage

Scout's intelligence remit spans six interlocking areas. Each should eventually be a first-class
tracked domain with its own sources, themes, opportunities, and risks.

1. **Publishing** — industry shifts, distribution models, rights, market movements.
2. **AI** — model releases, tooling, capabilities, costs, and regulatory developments relevant to
   AI-enabled publishing.
3. **Comics** — the comics industry, formats, platforms, and the path toward AI-assisted comic
   navigation.
4. **Phrasmos** — symbolic image tagging and metadata; advances and competition in this space.
5. **Caelaris** — the comic publishing project; its dependencies, opportunities, and threats.
6. **Strategic opportunities** — cross-domain synthesis: where AI, publishing, and comics intersect
   to create openings specific to Edenseek.

The distinctive value is not coverage of any single domain but **synthesis across them** — surfacing
opportunities that only appear when publishing, AI, and comics trends are read together.

---

## 4. Capability Pillars

The vision rests on five capabilities Scout must grow into. They are roughly sequential but
overlapping.

### 4.1 Durable Memory
A structured, deduplicated knowledge base — not a scratchpad. Themes, opportunities, and risks
accumulate across runs, are normalized, and persist as the system's long-term asset. This is the
foundation; everything else compounds on it. (First concrete step: "Memory v0.2" in the v0.4
roadmap.)

### 4.2 Active Research
Scout should gather information, not merely reason from a prompt. The dependency set already hints at
this intent (`requests`, `beautifulsoup4`). The target is a research loop: identify what to watch →
gather sources → extract signal → verify → record. Source provenance and recency should be tracked
alongside conclusions.

### 4.3 Synthesis & Strategic Reasoning
Beyond summarizing inputs, Scout should connect observations across domains and time, distinguish
durable signal from noise, and produce ranked, actionable recommendations tied to Edenseek's actual
projects.

### 4.4 Conversational Access
A chat interface over the accumulated knowledge base, so Derek (and future team members) can
interrogate what Scout knows — "what changed in AI publishing this month?", "what risks are we
tracking for Caelaris?" — rather than only reading reports.

### 4.5 Autonomy & Continuity
Reliable unattended operation: continuous monitoring, event-driven as well as scheduled outputs,
durable scheduling that survives restarts, graceful failure handling, and self-auditing of what it
has and hasn't covered.

---

## 5. Target Architecture (Conceptual)

This is a conceptual end-state, not a prescription of specific libraries. It is intentionally an
evolution of the current three-module design.

```
            ┌──────────────────────────────────────────────┐
            │                Interfaces                     │
            │   REST API  ·  Dashboard  ·  Chat interface   │
            └───────────────┬──────────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────────┐
            │              Orchestration                    │
            │  Scheduler · job queue · run lifecycle        │
            └───────────────┬──────────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────────┐
            │              Research Engine                  │
            │  source gathering → extraction → verification │
            │  → synthesis  (multi-step, per domain)        │
            └───────┬──────────────────────────┬───────────┘
                    │                          │
        ┌───────────▼─────────┐     ┌──────────▼───────────┐
        │   Knowledge Base    │     │     LLM Provider     │
        │  themes / opps /    │     │  (reasoning, synth)  │
        │  risks / sources /  │     └──────────────────────┘
        │  provenance         │
        └───────────┬─────────┘
                    │
        ┌───────────▼─────────┐
        │   Report Artifacts  │
        │   (Markdown, etc.)  │
        └─────────────────────┘
```

Key shifts from v0.3:
- **Knowledge Base** becomes the center of gravity (today: a near-empty JSON file).
- **Research Engine** sits between triggers and the LLM (today: a single direct LLM call).
- **Interfaces** gain a conversational surface (today: a read-only dashboard).
- **Orchestration** gains durable scheduling and a job lifecycle (today: an in-process cron job).

---

## 6. Design Principles for Contributors

These principles should guide every change so the system converges on the vision.

1. **Knowledge is the asset.** Optimize for the quality and durability of what Scout *knows*.
   Reports are a rendering of knowledge, not the goal.
2. **Every observation should be reusable.** Prefer structured, deduplicated, queryable outputs over
   one-off prose.
3. **Cite and date everything.** Track source and recency so conclusions are auditable and stale
   knowledge can be retired.
4. **Degrade gracefully.** Unattended autonomy demands timeouts, retries, and error handling; a
   failed source or LLM call must never corrupt the knowledge base.
5. **Secure by default.** Scout handles credentials and runs unattended; authentication, input
   validation, and least privilege are not optional. (The path-traversal exposure that once made the
   API key readable over HTTP — now fixed in commit fdf0ab8 — is the cautionary example of why; see
   the v0.3 synopsis.)
6. **Evolve, don't rewrite.** The three-module foundation is sound. Grow memory, research, and
   interfaces incrementally.

---

## 7. Trajectory

A high-level sequencing of the journey from v0.3 to the vision. Detailed near-term steps live in the
[v0.4 roadmap](./scout_v0.3_synopsis.md#10-v04-roadmap).

- **Near term (v0.4):** Structured, deduplicated memory ("Memory v0.2"); a `GET /memory` endpoint
  and dashboard surface; security hardening (auth, path-traversal fix, error handling). This makes
  *durable memory* real.
- **Mid term:** An active research loop that gathers and verifies external sources per domain, with
  provenance recorded in the knowledge base. This makes *active research* and *synthesis* real.
- **Longer term:** A conversational interface over the knowledge base; continuous and event-driven
  monitoring; durable, restart-safe orchestration. This makes *conversational access* and *autonomy*
  real.

Each phase is gated on the previous one's foundation: research is only as good as the memory it
writes to; conversation is only as good as the knowledge it draws from.

---

## 8. For Onboarding Agents & Developers

- Start with [`scout_v0.3_synopsis.md`](./scout_v0.3_synopsis.md) for the concrete current system.
- Treat this document as the "north star" — when a design choice is ambiguous, prefer the option
  that advances the capability pillars in §4 and respects the principles in §6.
- The original project intent is recorded in `README.md` and the execution brief at
  `archive/execution_brief_26_06_19`; this document consolidates and extends that intent.
- When you complete work that meaningfully advances a pillar, update the v0.3 synopsis (or its
  successor) so the "current state" and "vision" documents stay distinct and accurate.

## Operational Maturity Model

Scout is expected to evolve through four stages.

### Stage 1 — Alpha

Current state.

Characteristics:

- Single agent
- Daily reports
- Basic memory
- Manual oversight required

Goal:

Prove architecture and deployment model.

---

### Stage 2 — Beta

Characteristics:

- Reliable unattended operation
- Durable memory
- Structured report output
- Test coverage
- Security hardening

Goal:

Trust Scout to operate without supervision.

---

### Stage 3 — Intelligence Platform

Characteristics:

- Structured knowledge base
- Memory retrieval
- Source provenance
- Trend detection
- Conversational interface

Goal:

Institutional knowledge accumulation.

---

### Stage 4 — Autonomous Research Organization

Characteristics:

- Multiple cooperating agents
- Critic agent
- Strategist agent
- Research agent
- Publisher agent

Goal:

Generate, critique, refine, and distribute strategic intelligence with minimal human intervention.
