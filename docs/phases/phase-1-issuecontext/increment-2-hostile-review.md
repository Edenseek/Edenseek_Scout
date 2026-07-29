# Phase 1 · Increment 2 (thread `context` into the read path) — Hostile Review

**Scope reviewed:** `audit_s3_source.materialize_approved_contract` and `resolve_current_revision` gain an
optional `context=None`; `tests/test_audit_s3_source.py` gains a `TestIssueContextThreading` class.
No other module changed. No caller passes a context yet.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **`context=None` is byte-for-byte unchanged.** `git diff main -- audit_s3_source.py` shows the entire
  environment path is the *same statements re-indented* under a new `else:` — no env line altered, dropped,
  or reordered, and the shared `client = _s3_client(region)` is untouched. The 226 pre-existing tests (which
  all call with no context) pass unmodified.
- **Context path == env path — proven.** `test_resolve_current_revision_context_equals_env` and
  `test_materialize_context_equals_env` run both paths and assert identical pointer dict, identical S3
  `GetObject` keys, identical dest `series/issue` path, and **byte-identical provenance**. This holds because
  `IssueContext` reproduces the env derivation byte-for-byte (Increment 1).
- **Exception semantics preserved.** The env path still raises `ScoutS3SourceError` (not `IssueContextError`)
  and still requires only the *approved* env vars. The env branch was deliberately **not** routed through
  `IssueContext.from_env()` — doing so would change the exception type (breaking the `ScoutS3SourceError→503`
  handler + tests) and would additionally require the Scout *write* env. This divergence is intentional and
  documented; the from_env unification lands only once the runners build the context at entry (Increment 4).

### Ownership boundary (must never regress)
- **Read-only on the context path too.** `test_context_never_writes` asserts no `put_object`/`delete_object`
  when driven by a context. Still `GetObject`-only; nothing can write `edenseek-publishing`.

### Self-containment + precedence
- **Works with the environment cleared.** Both equivalence tests run the context path under
  `mock.patch.dict(os.environ, {}, clear=True)` — the context needs no environment.
- **Context overrides the environment.** `test_context_overrides_environment` sets a *wrong* env prefix and
  confirms the reads use the context's prefix, not the env's.

### Scope creep + coupling
- **Only `audit_s3_source` touched.** No Registry/scheduler/dashboard. `audit_s3_source` does **not** import
  `scout_context` — it only reads attributes off the passed object, so no import cycle is introduced and the
  leaf remains a leaf.
- **No new required argument.** `context` defaults to `None`; every existing caller
  (`dataset_auditor.materialize_approved_contract()`, `resolve_current_revision(client)`) is unchanged and
  green.

## Evidence
- `git diff main -- audit_s3_source.py`: env path = pure re-indent (38 ins / 22 del, all indentation + the
  additive context branch).
- Read-path tests: **13 passed** (9 existing + 4 new).
- Full suite (venv): `python -m unittest discover -s tests` → **230 passed, 0 failures**.
- `py_compile` clean.

**Gate to proceed to Increment 3 (thread `context` into persistence + index + ledger, one module per
commit):** founder certification of this increment.
