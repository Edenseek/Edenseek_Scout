# Phase 1 · Increment 3 (thread `context` into persistence + index + ledger) — Hostile Review

**Scope reviewed:** optional `context=None` threaded through the Scout **write** surface —
`scout_report_publisher` (3a), `scout_report_index` (3b), `scout_revision_ledger` (3c) — one module
per commit (`7599837`, `50d0c9e`, `8882a3f`), each with equivalence tests. No caller passes a context yet.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **`context=None` is byte-for-byte unchanged.** For all three modules the env path is the same
  statements re-indented under a new `else:`. `git diff main` shows every "…is not configured" error
  string balanced exactly once removed / once added (pure indentation) — no message altered, and the
  distinct variants ("target" vs "write target … there is no local fallback") are each preserved verbatim.
- **Context path == env path — proven at the byte level.** Equivalence tests assert the **entire
  in-memory S3 store is identical** env-vs-context (env cleared) for the persistence transaction:
  - publisher: `publish_scout_report` + `publish_delta_report` stores byte-identical; `list_history_keys`,
    `read_object`, `last_published_revision_id` return identical values.
  - index: `load_index`/`update_index`/`rebuild_index` yield identical dicts + a byte-identical
    `report_index.json`.
  - ledger: `mark_processed`/`mark_failed` write a byte-identical `processed_revisions.json`
    (with `_now` pinned so wall-clock can't mask a real diff), `load_ledger` identical.
- **Whole-system behavior unchanged.** No production caller (`app.py`, `scheduler.py`, `scout_watch.py`,
  `dataset_auditor.py`, `scout_delta_audit.py`) passes a context — verified by grep. The 243-test suite
  passes with those callers untouched, so the certified single-issue path is byte-for-byte intact.

### Ownership boundary (must never regress)
- **Context path writes only `edenseek-scout`.** Each module's threading tests assert every written key is
  under `edenseek-scout` / `issues/issue_001/`; no deletes, no Publisher-bucket writes.
- **Read/write surfaces stay separate.** The write modules read only `context.scout_*`; the approved
  (read) surface is never consulted here.

### Precedence + self-containment
- **Works with the environment cleared** (every equivalence test runs the context path under
  `clear=True`) and **overrides a wrong env prefix** (publisher `test_context_overrides_env_and_writes_only_scout`).

### Scope creep + coupling
- **Only the three write modules changed** (+ their tests). No Registry/scheduler/dashboard.
- **Choke-point threading.** index/ledger route through their single `_index_context`/`_ctx` helper, so the
  context enters each module in exactly one place; the publisher's per-function `else:` blocks are verbatim.
- **No import cycle.** The modules read attributes off the passed context object; only the *tests* import
  `scout_context`. `scout_context` remains a leaf.
- **No new required argument.** All 12 threaded entry points default `context=None`.

## Note carried forward (inert)
Region reads in `_index_context`/`_ctx` moved from the inline `_s3_client(os.getenv(...))` call into the
`else:` branch as a `region` variable, then a shared `client = client or _s3_client(region)`. Same region
string, same client — behavior-neutral; proven by the byte-identical index/ledger objects.

## Evidence
- `git diff main` (3 modules): env paths = pure re-indent; all error strings balanced.
- New equivalence tests: publisher +5, index +4, ledger +4.
- Full suite (venv): **243 passed, 0 failures** (was 230 before Increment 3).
- `py_compile` clean for all three modules + their test files.

**Gate to proceed to Increment 4 (thread `context` into the runners `scout_delta_audit` + `dataset_auditor`,
where a context is first *built* at entry):** founder certification of this increment.
