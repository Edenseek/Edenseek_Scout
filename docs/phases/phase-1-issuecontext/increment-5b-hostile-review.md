# Phase 1 · Increment 5b (thread `context` into `scout_archive`) — Hostile Review

**Scope reviewed:** optional `context=None` on `scout_archive.build_archive`, forwarded to the
already-threaded `sri.load_index` and `ledger.load_ledger`. `scout_archive` has **no direct env reads** of
its own — it is a pure projection over the index + ledger — so this is the thinnest possible increment.

## Verdict: PASS

### Behavioral equivalence
- **`context=None` is byte-for-byte unchanged.** `git diff main -- scout_archive.py` is three lines: the
  signature gains `context=None`, and the two delegate calls gain `context=context`. When `context is None`,
  `load_index(client, context=None)` and `load_ledger(client, context=None)` are exactly the prior calls
  (Increment 3 certified those as byte-for-byte). No other logic changed; `parse_query`/`search_archive`
  remain pure and untouched.
- **Context path == env path.** `test_build_archive_context_equals_env` seeds an index (2 reports) + a
  failed ledger entry, then builds the archive under the env default vs an explicit context **with the
  environment cleared**, asserting the archive dicts are identical (2 reports, 1 failed).
- **Whole-system behavior unchanged.** Both production callers — `app.py:308` and `app.py:320` — call
  `build_archive()` with no context, so `context=None` → the certified env path.

### Scope + boundary
- **Read-only projection.** `build_archive` performs no writes; the increment adds no write path.
- **Only `scout_archive.py` changed** (+ its test). No activation (`from_env()` not introduced); no new
  required argument.

## Evidence
- `git diff main -- scout_archive.py`: signature + two delegate calls only.
- New test: **+1** (`TestArchiveIssueContextThreading`).
- Full suite (venv): **257 passed, 0 failures** (was 256 after 5a).
- `py_compile` clean.

**Gate to proceed to Increment 5c (`scout_intelligence` — forwards to `load_index` + `read_object`):**
founder certification.
