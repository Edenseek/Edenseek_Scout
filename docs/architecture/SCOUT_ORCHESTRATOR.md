# Scout Orchestrator

> How Scout coordinates runs, memory, and continuity briefings.
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: fdf0ab8

## 1. Current Run Lifecycle (as-built)

```
trigger (cron 08:00 local | POST /run-scout)
   → generate_report()
      → load_memory()                # data/memory.json, locked
      → call_openai_with_retries()   # gpt-4o-mini, 3x retry, 60s timeout
      → write reports/<timestamp>.md
      → update + atomically save memory (report_count, last_report)
```

Single process, in-process APScheduler, no job store. (See `scout.py`, `scheduler.py`.)

## 2. Target Run Types (v0.4+)

Scout grows from one run type to three, all sharing the same reliability primitives
(lock + atomic write + retry):

| Run type           | Trigger               | Output |
|--------------------|-----------------------|--------|
| Strategic Report   | daily cron, manual    | Narrative report + extracted memory (Memory v0.4) |
| Intake Report      | session start, manual | Continuity briefing (see `REPORT_SPECIFICATION.md` §3) |
| Memory Maintenance | post-report           | Extraction, dedup, normalization into per-project memory |

## 3. Memory v0.4 Pipeline

```
report generated
   → extract {themes, opportunities, risks} as structured JSON (per project)
   → normalize + dedupe against existing memory (stable keys)
   → merge with provenance (source, first_seen, last_seen)
   → atomic write to data/memory.json
```

The extraction step is additive: the existing narrative report is unchanged; structured
fields are produced alongside it (see `REPORT_SPECIFICATION.md` §2). Per-project records
also carry `active_milestone`, `next_action`, `last_verified_commit`, and `open_questions`
(see `PROJECT_MEMORY_SCHEMA.md` §2.2), which the Intake Report consumes directly.

## 4. Intake Report Assembly

The Intake Report is a **read-only aggregation** of signals Scout already holds plus a
git snapshot:

```
git read-only introspection  ──┐
memory (per-project state)    ──┤
schedule position             ──┼──▶ assemble Intake Report ──▶ reports/intake/<ts>.md
architecture-compliance check ──┤
recommended tasks (derived)   ──┘
```

Git introspection is strictly read-only (`branch`, `rev-parse`, `log`, `status`,
`diff --stat`). No write git operations are ever invoked (Charter §4).

## 5. Boundary Enforcement

The orchestrator is the choke point for Charter §4. It exposes no code-editing, commit,
or deploy capability. Any "recommended task" is emitted as text for a human/agent to act
on — never executed. Git access is mediated through a read-only helper that whitelists
non-mutating subcommands.

## 6. Known Operability Gaps (carried from baseline)

- `/run-scout` is synchronous/blocking.
- Scheduler has no durable job store; state rebuilds on restart.
- No scheduler health endpoint; dashboard schedule is hardcoded.
- Startup still uses deprecated `@app.on_event("startup")`.
