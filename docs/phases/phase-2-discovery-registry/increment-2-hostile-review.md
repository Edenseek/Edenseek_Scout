# Phase 2 · Increment 2 (Registry resolution — read-only) — Hostile Review

**Scope reviewed:** added read-only resolvers to `scout_registry.py` — `resolve_entry` /
`resolve_registry` (+ `_resolve_review_id` / `_resolve_publication_state` / `_resolve_audit_linkage`) —
that derive a Registry from authoritative Publisher objects (current revision + platform-approval
state) and Scout's own index/ledger (audit linkage). New tests in `tests/test_scout_registry.py`.
**No persistence, no production consumer, no existing module changed.**

## Verdict: PASS

### Behavioral equivalence (core risk)
- **Byte-for-byte preserved.** `git diff main` touches only `scout_registry.py` + its test (+ this doc);
  no existing production module changed. Nothing imports `scout_registry`, so no production code path
  changed. Full suite **279 passed** (272 prior + 7 new).

### ADR conformance
- **D3 — derived, read-only, rebuildable.** Resolution performs **GET-only** reads and writes nothing;
  the Registry is recomputed by re-resolving (idempotent by construction). It reads the Publisher's
  authoritative objects (`approved/published.json` → revision; `reviews/{id}/platform_approval.json` →
  state) — **never** the stale `dataset_registry.json`.
- **Facts vs. observations (Principle P1).** `publication.state` records the **verbatim**
  `canonical_dataset_state` from `platform_approval.json` (Publisher fact), with absence ⇒
  `creator_approved` and denied/unparseable ⇒ `unknown`. Scout's audit linkage is derived separately from
  Scout's own index/ledger — never conflated with Publisher state.
- **Reuse, not duplication.** Resolution reuses the certified, context-threaded readers
  (`audit_s3_source.resolve_current_revision` / `probe_object`, `scout_report_index.load_index`,
  `scout_revision_ledger.load_ledger`); `_resolve_review_id` mirrors `audit_review._derive_review_id` and
  is **drift-guarded** by `test_review_id_matches_audit_review`.

### Robustness / failure modes
- **Tolerant resolution.** A resolvable-but-unpublished issue (no pointer) yields a fact-free tree-of-one
  entry rather than raising (`test_unpublished_when_no_pointer`); missing/denied platform_approval and an
  absent index/ledger degrade to `creator_approved`/`unknown` and `unprocessed` — never a crash.
- **Audit states covered:** audited (index entry for the current revision), failed (ledger failure for the
  current revision), unprocessed (neither) — all tested.

### Scope + coupling
- **Read-only.** No `put`/`delete`; cannot write either repository. No persistence yet (deferred to
  Increment 3).
- **No import cycle.** `scout_registry` now imports `audit_s3_source` / `scout_report_index` /
  `scout_revision_ledger` — none of which import `scout_registry` (verified). The Registry sits above the
  Audit-layer readers.
- **No production consumer.** No production module imports `scout_registry`; the operational surface is
  untouched.
- **In-milestone.** Resolution only — no persistence, no Discovery, no scheduler wiring.

## Evidence
- `git diff main`: only `scout_registry.py` + `tests/test_scout_registry.py` (+ this doc).
- New tests: **+7** (`ResolveTest`), incl. the review-id drift guard.
- Full suite (venv): **279 passed, 0 failures** (was 272).
- `py_compile` clean.

**Gate to proceed to Increment 3 (persist the resolved Registry to `edenseek-scout` as a derived,
rebuildable projection — R1 object-key contract + readback verification):** founder certification.
