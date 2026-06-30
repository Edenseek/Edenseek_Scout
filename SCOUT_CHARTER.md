# Scout Charter

> The single authoritative governing charter for Edenseek Scout.
> This document defines Scout's identity, mission, and operating boundaries.
> All architecture documents and specifications derive from it.
> Last verified against commit: fdf0ab8

---

## 1. What Scout Is

Edenseek Scout is the **Dataset Intelligence Layer** for Edenseek Publishing, operating as a
**Publisher Lifecycle Audit Sidecar** — a bounded, read-only, deterministic system that
observes the permitted repository artifacts emitted by each Publisher lifecycle phase and
produces structured intelligence about their quality. Each Publisher lifecycle phase emits
repository artifacts; Scout reads only the permitted artifacts for that phase, performs
comparisons appropriate to that phase, and writes only Scout reports. It is the **first
operational Dataset Intelligence System** within the broader Edenseek ecosystem, intentionally
deterministic and non-autonomous: it does not plan, use tools, or take actions.

Ownership is fixed: **Publisher** owns creation, **humans** own approval, the **Repository**
owns storage, and **Scout** owns observation, comparison, diagnostics, and reporting. Scout
never modifies Publisher data, never approves content, never becomes the source of truth, and
never bypasses human approval. Per-phase reads are observation-only and advisory; findings
return to the Publisher workflow for human correction.

Scout serves **two audiences from the same deterministic outputs**:

- **Humans** — Derek and publishers, who need to know what to review, what is wrong, and
  whether quality is improving.
- **AI engineering agents** — ChatGPT, Claude Code, and future Edenseek agents, which need
  structured, machine-readable intelligence on *why* the dataset is failing and which part
  of the creation / enrichment / approval / retrieval pipeline to improve.

Scout's product is **knowledge and quality intelligence**, not reports. Reports, quality
scores, queues, and failure analyses are renderings of what Scout knows about the datasets
it audits.

Scout is **diagnostic, not prescriptive of action**: it identifies and explains problems
and surfaces where they cluster, but it does not act, approve, or change the system. Scout
**does not** create canonical data, approve metadata, or bypass publisher review. All
production changes remain subject to human authority.

---

## 2. Mission

Improve the quality, reliability, and strategic value of Edenseek's publishing datasets by
continuously inspecting publisher-side artifacts and surfacing — for human review — where
quality is weak, incomplete, or at risk.

Scout generates:

- dataset quality audits
- metadata quality reports
- character and dialogue analysis reports
- retrieval-readiness reports
- weak-artifact queues
- improvement recommendations and quality scores

---

## 3. Vision

A persistent AI intelligence layer that continuously improves publisher datasets, metadata
quality, character recognition, dialogue extraction, reference-material utilization,
retrieval readiness, and reader trust — while maintaining complete publisher ownership and
approval authority.

Scout becomes the **quality-control intelligence layer** for the Edenseek platform.

---

## 4. Operating Boundaries (Non-Negotiable)

Scout is **read-and-advise only.** It inspects, scores, reports, and recommends — nothing
more. Execution is always a human-initiated decision.

Scout MAY:

- inspect the permitted repository artifacts of each Publisher lifecycle phase (per the Scout
  Data Access Contract): intake artifacts, processing artifacts, metadata-generation drafts,
  human-review/approval **state summaries** (read, never set), the approved dataset, approved
  metadata, reference materials, and Dataset Registry records — phase reads are
  observation-only and advisory
- inspect retrieval evidence packets (to assess readiness, never to perform retrieval)
- read its own memory and call its LLM provider
- write its own reports, quality scores, and memory files
- recommend improvements and surface risks, opportunities, and questions for humans/agents

Scout MUST NOT:

- modify canonical Edenseek/publisher data, at any lifecycle phase
- approve, reject, or lock metadata or artifacts, or bypass publisher review
- act as or become a phase approval gate, an approval authority, or the source of truth at any
  lifecycle phase (Scout reports on review/approval state; it never sets it)
- rewrite prompts, or automatically apply prompt/enrichment/data changes
- change its own scoring rules, failure taxonomy, or configuration autonomously
- modify itself or its behavior based on its own history (it may *report* on history,
  never *self-modify* from it)
- rely on LLM, embedding, vision, or external network calls to produce its dataset-audit
  reports — those reports are deterministic and offline (JSON parsing, counting, structural
  analysis) and never interpret raw comic images (see "Two report families" below)
- implement or act as a search/retrieval engine, or alter retrieval results
- generate reader-facing narrative answers on behalf of Edenseek
- write, modify, or refactor project code; create commits/branches/tags/pushes
- deploy, restart services, or change infrastructure
- take any irreversible or outward-facing action autonomously

All recommendations and analyses are advisory and require explicit human review.

**Two report families (a documentation distinction — no behavior change).** Scout's
**dataset-audit reports** (dataset quality, character/dialogue analysis, retrieval-readiness,
weak-artifact queues, failure analysis) are the deterministic, offline reports the boundaries
above govern — JSON parsing, counting, and structural analysis, with **no LLM, embedding,
vision, or raw-comic-image interpretation**. These are the reports that participate in the
Publisher-workflow audit. Scout's separate **strategic / narrative reports** (the scheduled
market/strategic intelligence narrative) are LLM-generated; they never read the canonical
repository's comics, never mutate canonical data, never approve a phase, and do not
participate in the Publisher-workflow audit. The deterministic, no-LLM guarantee applies to
the dataset-audit reports.

---

## 5. Principles

1. **Knowledge is the asset.** Optimize for what Scout durably knows about dataset quality.
2. **Determinism over prose.** Prefer repeatable, auditable scoring to one-off narrative.
3. **Cite and date everything.** Every finding carries the artifact, source, and recency.
4. **Reliability before intelligence.** Never corrupt memory; degrade gracefully.
5. **Evolve, don't rewrite.** Grow the three-module foundation incrementally.
6. **Advise, never act.** See §4. Scout proposes; humans dispose. Human approval is the
   final authority.
7. **Deterministic and cheap.** Dataset-audit reports are produced by JSON parsing, counting,
   and structural analysis — no LLM, embedding, vision, or external-service calls — so they are
   safe to run on every audit and after every pipeline change. (Scout's separate strategic /
   narrative reports are LLM-generated and do not participate in the Publisher-workflow audit.)
8. **No autonomous self-modification.** Scout may read its own historical reports and audit
   history to report trends, but never changes its scoring rules, taxonomy, or
   configuration on its own.
9. **Serve humans and agents alike.** Every report pairs a human-readable rendering with a
   stable, machine-readable structure so AI engineering agents can consume it.

---

## 6. Lifecycle Audit Architecture

```text
Each Publisher lifecycle phase emits repository artifacts (read-only):
  Intake -> Processing -> Metadata Generation -> Human Review -> Approved Dataset -> Canonical Repository
        |  (Scout reads only the permitted artifacts for each phase)
        v
     Scout (observation, comparison, diagnostics)
        |
        v
Audit Reports / Quality Scores / Improvement Proposals (written only to Scout's report space)
        |
        v
Publisher workflow + Human Review (decide corrections)
```

The canonical end-to-end Publisher workflow that emits these artifacts is defined in the
Edenseek repository at `docs/architecture/publisher_workflow.mmd` (the approved source of
truth); Scout audits the artifacts that workflow produces and never alters it. Scout's audit
reports and findings constitute the **Audit / Correction Ledger** referenced by that Publisher
Architecture — written only to Scout's report space and returned to the Publisher workflow for
human correction.

Primary inputs (read-only, by phase — per the Scout Data Access Contract):

- intake artifacts; processing artifacts; metadata-generation drafts
- human-review / approval **state summaries** (read, never set)
- the approved dataset: `approved_dataset.json`, `approved_llm_outputs.json`, `retrieval_evidence_packets.json`
- reference materials (scripts, character sheets, creator notes); Dataset Registry records

The **Approved Dataset** phase is active today; pre-approval phases are defined in the Scout
Data Access Contract and activated incrementally as each phase's comparisons and reports are
validated.

Primary outputs (written only to Scout's own report/memory space):

- dataset quality reports
- character analysis reports
- dialogue analysis reports
- retrieval-readiness reports
- weak-artifact queues

---

## 7. Success Criteria

Scout is successful when it can:

1. Operate continuously without supervision.
2. Maintain persistent, structured project memory.
3. Produce repeatable dataset quality audits.
4. Identify metadata weaknesses before human review.
5. Improve character-recognition quality.
6. Improve dialogue-extraction quality.
7. Improve retrieval readiness.
8. Support publisher decision-making.
9. Preserve publisher control over all canonical data.
10. Provide conversational access to institutional knowledge.

---

## 8. Product Roadmap

| Phase | Focus | Result |
|-------|-------|--------|
| Phase 1 — Dataset Intelligence ✅ | Dataset auditor, metadata quality scoring, weak-artifact detection, character/dialogue analysis | Scout audits dataset quality |
| Phase 2 — Publisher Intelligence ✅ | Review prioritization, page heat map, audit history + trend | Scout knows what to review next |
| **Phase 3 — Dataset Failure Analysis** | Root-cause aggregation, highest-leverage failure, failure clusters, retrieval blockers | Scout explains *why* the dataset is failing |
| Phase 4 — Historical Intelligence | Trend, regression, and intervention-effectiveness over audit history | Scout shows what improved and what recurs |
| Phase 5 — Retrieval Readiness Intelligence | Deeper retrieval-readiness / evidence-packet / coverage analysis | Scout assesses how ready the dataset is for retrieval (never a retrieval engine) |
| Phase 6 — Reader Trust Intelligence | Hallucination, citation, reader-trust, and refusal analysis | Scout assesses the dataset's reader-trust readiness |
| Phase 7 — Coordinated Intelligence Ecosystem | Dataset, search-readiness, and reader-trust intelligence coordinated with critique and strategy | An Edenseek dataset-intelligence platform |

The current active phase is **Phase 3 — Dataset Failure Analysis**.

Future **agent identities** (e.g. specialized search, reader-trust, critic, or strategist
roles) are **roadmap concepts, not charter commitments**. This charter defines Scout's
purpose and boundaries only; the evolving agent/system structure lives in
`docs/architecture/scout_beta_roadmap.md`.

---

## 9. Long-Term Strategic Role

Scout is intended to become the **publisher-side intelligence layer** of the Edenseek
ecosystem: continuously improving dataset quality, metadata quality, retrieval readiness,
and institutional knowledge while preserving human authority over all canonical publishing
data.

Knowledge becomes the asset. Reports become one view of that knowledge. Human approval
remains the final authority.
