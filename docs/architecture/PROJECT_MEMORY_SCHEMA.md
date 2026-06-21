# Project Memory Schema

> The contract for `data/memory.json` across versions.
> Derives from `SCOUT_CHARTER.md`. Last verified against commit: fdf0ab8

## 1. Current Schema (v0.3, as-built)

```json
{
  "report_count": 0,
  "themes": [],
  "opportunities": [],
  "risks": [],
  "last_report": null
}
```

Only `report_count` and `last_report` are mutated today; the list fields are read into the
prompt but never written back. Writes are atomic and lock-guarded.

## 2. Target Schema (v0.4)

Memory becomes **per-project and structured**, with provenance and dedup keys.

```json
{
  "schema_version": "0.4",
  "report_count": 0,
  "last_report": null,
  "last_intake": null,
  "projects": {
    "edenseek": {
      "active_milestone": null,
      "next_action": null,
      "last_verified_commit": null,
      "open_questions": [],
      "themes": [],
      "opportunities": [],
      "risks": []
    },
    "phrasmos": {
      "active_milestone": null,
      "next_action": null,
      "last_verified_commit": null,
      "open_questions": [],
      "themes": [],
      "opportunities": [],
      "risks": []
    },
    "caelaris": {
      "active_milestone": null,
      "next_action": null,
      "last_verified_commit": null,
      "open_questions": [],
      "themes": [],
      "opportunities": [],
      "risks": []
    }
  },
  "cross_project": { "themes": [], "opportunities": [], "risks": [] }
}
```

### 2.1 Memory item shape

Every theme / opportunity / risk is an object, not a bare string:

```json
{
  "id": "stable-hash-of-normalized-title",
  "title": "short normalized label",
  "detail": "one-to-two sentence description",
  "first_seen": "ISO-8601",
  "last_seen": "ISO-8601",
  "occurrences": 1,
  "source": "report:<filename> | external:<url> | inferred",
  "status": "active | watching | retired"
}
```

### 2.2 Per-project continuity fields

Each project record carries four continuity fields that feed the Intake Report directly:

| Field                  | Type            | Meaning | Intake Report section |
|------------------------|-----------------|---------|-----------------------|
| `active_milestone`     | string \| null  | The milestone this project is currently working toward. | Current Milestone |
| `next_action`          | string \| null  | The single most important next step (advisory only). | Recommended Tasks |
| `last_verified_commit` | string \| null  | Short SHA the project state was last reconciled against. | Architecture Warnings (drift vs. current commit) |
| `open_questions`       | array of strings| Unresolved questions awaiting a human/agent decision. | Questions for Claude / Questions for ChatGPT (routed by topic) |

These fields are **descriptive state, never executable instructions** (Charter §4).
`next_action` and `open_questions` are surfaced for humans/agents to act on; Scout never
executes them.

## 3. Deduplication Rule

Items are keyed by `id` = stable hash of the normalized title. On merge: existing item →
bump `occurrences`, update `last_seen`; new item → insert with `first_seen = last_seen`.
Stale items (no `last_seen` update for N runs) transition to `retired`.

## 4. Migration (v0.3 → v0.4)

- Read-only, idempotent migration on first v0.4 load.
- Preserve `report_count` and `last_report`.
- Seed `projects.*` with empty continuity fields and lists; do not fabricate history.
- Bump `schema_version`; keep a one-time backup copy before first write.

## 5. Invariants (Charter §4 / reliability)

- All writes atomic (temp → fsync → replace) and lock-guarded (already implemented).
- A failed extraction must never partially overwrite memory — extract fully, then merge.
- Memory is data, never code; Scout never executes anything read from memory.
