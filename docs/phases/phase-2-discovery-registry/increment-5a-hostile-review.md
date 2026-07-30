# Phase 2 · Increment 5a (governed Registry rebuild trigger) — Hostile Review

**Scope reviewed:** `scout_registry.rebuild_current` + a CLI (`main` / `__main__`) — the governed one-shot
that materializes the persisted Registry for the env-configured single issue (tree-of-one) from
authoritative Publisher data, plus a test. Also executed **live against production** to validate the
complete Registry lifecycle against real data.

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Certified audit path untouched.** No certified audit-path module changed in Phase 2 (`scout_delta_audit`,
  `dataset_auditor`, `audit_review`, `audit_s3_source`, `scout_report_publisher/index`,
  `scout_revision_ledger`, projections, `scout_context` — all byte-for-byte identical to `main`). The only
  production files Phase 2 has touched are `app.py` (Increment 4, additive read routes) and the new
  `scout_registry.py`. This increment extends only `scout_registry.py` + its test.
- **First `from_env()` in a real entry point — but a SEPARATE tool.** `rebuild_current` builds the context
  via `IssueContext.from_env()`. This is deliberate and isolated: it is a **new, human-run operational
  tool**, not the certified audit path. The audit runners still pass `context=None` and run their env
  branches unchanged — activation of `from_env()` inside the audit flow remains a separate future decision.

### Ownership + safety
- **Read-only on the Publisher; writes only `edenseek-scout`.** Resolution is GET-only; the sole write is
  `registry/registry.json` in the Scout bucket. The test asserts the write is confined to `edenseek-scout`,
  and the live run wrote only that key (`bucket: edenseek-scout`). Cannot reach `edenseek-publishing` (IAM
  Deny + fixed root key).
- **Governed / one-shot.** Human-run CLI — no scheduler, no automatic trigger, no HTTP write endpoint. Runs
  once when invoked; no background behavior.
- **Integrity.** Persist reuses the certified `srp._put`/`_verify_readback` (readback SHA-256), so a
  corrupted write fails loud. The CLI fails loud (log + exit 1) on any error.

### Live production validation (the increment's purpose)
- Ran `python scout_registry.py` against production. Result: `registry/registry.json` persisted + verified
  (`sha256 a5354b10…`, count 1), resolved entirely from **real authoritative data**:
  `publisher=edenseek / society_universe / society_of_killers / issue_001`; publication
  `rev_0be8dc34` / review `rev_0be8dc342ab3` / state **`edenseek_approved`** (verbatim Publisher fact);
  audit **`audited`** / `run_seq 3` / `run_833dfc915be60481` / `run000003`.
- The resolved audit linkage **cross-matches the certified Phase-1 baseline exactly** (same run_id /
  run_seq / report_id), confirming the Registry observes Scout's own certified state correctly.
- An **independent read-back** (`load_registry` + `tree_view`) confirmed the persisted object loads and the
  D6 tree view resolves (`edenseek → society_universe → society_of_killers → issue_001`).

### Scope + coupling
- **Only `scout_registry.py` + its test changed** this increment. No scheduler, no Discovery, no dashboard.
- No new import cycle (unchanged import set + stdlib `datetime`/`sys`).

## Notes
- **Determinism:** re-running overwrites `registry/registry.json` with identical content **except**
  `generated_at` (a wall-clock projection timestamp) — expected for a latest-state, rebuildable projection.
- **Not deployed:** the live rebuild was a governed one-shot from this session; the Oracle VM is not running
  Phase-2 code. `GET /registry` is live only once Phase 2 is deployed — but the persisted object now exists
  and would be served.

## Evidence
- `git diff main`: certified audit-path modules unchanged; this increment touches only `scout_registry.py`
  + `tests/test_scout_registry.py`.
- New test: **+1** (`test_rebuild_current_governed_one_shot`) — env-driven `from_env`, resolve→persist,
  loads back with revision + verbatim state + audit linkage, writes only the Scout bucket.
- Full suite (venv): **288 passed, 0 failures** (was 287).
- Live prod one-shot: persisted + readback-verified + independently re-read.
- `py_compile` clean.

**Gate to proceed to Increment 5b / Discovery (enumerate issues publisher-wide to build the contexts the
Registry is resolved over):** founder certification.
