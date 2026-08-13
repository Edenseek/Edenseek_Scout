# Certification Report — Multi-Issue Dataset Audit (intake-seam fix, Option A)

**Track:** Cross-repo intake seam · **Branch:** `week13-multi-issue-dataset-audit`
**Date:** 2026-08-13 · **Discipline:** certified-first (build → adversarial review → certify → deploy → verify)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for merge → deploy → re-intake cert

---

## 1. What changed and why

Edenseek's intake (`scout_report_intake.py`) ingests only the **consolidated `scout_report_`** — produced by
`dataset_auditor.run_dataset_audit` — to compose Publisher Diagnostics / Review Records. But Scout produced
that consolidated report **only for the single env-configured issue** (both callers — `POST /run-audit` and
the scheduler — invoke `run_dataset_audit()` with no context). The delta audit was made multi-issue in
Increment 1; the dataset audit never was. So newly-published issues (`promises`, `i_ride_for_them`) had
**only** delta reports → intake found nothing → Diagnostics read *"No Review Records"* (it fooled the founder).

Johnny confirmed **Option A** (Scout emits the contract artifact per issue; hold B — no intake change): the
consolidated `scout_report_` is the ratified Scout↔Edenseek Diagnostics/governance contract; the delta report
is Scout's own analytical artifact.

## 2. Change

- **`dataset_auditor.dataset_audit_all_discovered(client=None, force=False, trigger=…)`** (new) — enumerates
  `scout_discovery.discover_contexts()` and runs `run_dataset_audit(context=ctx)` per issue. **Orchestration
  only:** `run_dataset_audit` already threads `context` through the input
  (`materialize_approved_contract(context)`), the provenance (`load_source_provenance` of the per-context
  input → `publisher_revision_id`/`_key`), the `issue_id`, and the write path
  (`publish_scout_report`/`publish_reports` use `context.issue_id` + `context.scout_prefix`) — so each
  issue's report is written under its **own `{issue_prefix}/history/` prefix carrying its own identity**,
  with **no field changes**. **Idempotent:** skips an issue whose latest consolidated report already covers
  its current published revision (`last_published_revision_id(ctx) == resolve_current_revision(ctx).revision_id`),
  unless `force`. **Per-issue isolation** (mirrors the delta `audit_all_discovered`).
- **Folded into `--all`:** `scout_delta_audit.audit_all_discovered(..., dataset=False)`; `dataset=True` runs
  the consolidated audit and records it under `result["dataset"]`, wrapped so a failure is **non-fatal** (the
  delta reports are already persisted). The CLI `--all` and `POST /run-delta-audit-all` opt in. One command →
  delta + consolidated reports + rebuilt projections; idempotency prevents churn on unchanged issues.
- **Backward-compat:** `dataset=False` default → no `dataset` key, `dataset_auditor` not imported/executed —
  byte-identical to the certified Increment-1 orchestrator.

## 3. Intake requirement (Johnny's hard requirement) — met by construction

Intake derives the Review Record key from the S3 path (`{issue_prefix}/history/`) and reads
`issue_id`/`publisher_revision_id`/`publisher_revision_key` from the body. All four are context-derived per
issue (§2), so a per-issue consolidated report lands under the right prefix with the right identity and
intake needs **no change** — same `scout_report_` stem + shape.

## 4. Tests

Full suite **500 passed** (+8). `tests/test_dataset_audit_all.py`: audits each non-current issue; **idempotent
skip** when the latest report covers the current revision; **`force`** re-audits; **per-issue isolation** (one
error, run continues). `tests/test_multi_issue_audit.py`: `dataset=True` records `dataset` + calls the
orchestrator; default `dataset=False` (no key, orchestrator not called); a dataset-audit failure is
**non-fatal** (recorded, audit counts intact); the endpoint opts in.

## 5. Adversarial review (one round + fold)

The reviewer **could not break the central claim** — the consolidated `scout_report` (the intake artifact) is
correctly per-issue: every context path (`materialize_approved_contract`, `load_source_provenance`,
`publish_scout_report`/`publish_reports`) uses only the per-issue context; the env branch (`_require_issue_prefix`
/ `SCOUT_REPO_S3_PREFIX`) is strictly the `context is None` fallback; each issue's temp dir is unique.
Idempotency, isolation, non-fatal folding, no-churn, backward-compat, and no import cycle all verified clean.
It found **one MAJOR I introduced** (in a *secondary* artifact) + one MINOR:

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MAJOR | `run_dataset_audit` records into the single **global** `edenseek_dataset` memory track, so a multi-issue `--all` interleaves issues: each issue's co-published **`audit_history` report** embedded other issues' snapshots + a wrong cross-issue `latest_delta`, and `build_historical_intelligence` (the "most-recent dataset") would analyze whichever issue ran last. (The consolidated intake artifact was already clean — it doesn't include `audit_history`.) | **Fixed, two parts:** (a) the published `audit_history` block **and** the `historical` block are now built from a `dataset_id`-filtered `issue_history`, so each issue's report carries only its own snapshots + a correct within-issue delta; (b) `record_audit_history` now caps **per `dataset_id`** so a busy issue can't evict a quiet one's snapshots. Both are no-ops for a single-issue history (byte-identical). |
| 2 | MINOR | `SCOUT_DATASET_DIR` (a single-issue local override) was honored before `context`, so under that misconfig every issue would read the same local dir. Latent (unset in prod). | **Fixed** — `SCOUT_DATASET_DIR` is ignored when a per-issue `context` is present. |

New tests: `record_audit_history` caps per `dataset_id` (a busy issue doesn't evict a quiet one);
`dataset_audit_all_discovered` calls `run_dataset_audit` with each issue's **own** context (the per-issue
threading). Suite **501 passed**.

## 6. Certification statement

Additive orchestration over the already-context-threaded dataset audit; the consolidated intake artifact is
per-issue with correct identity + write-path (no field changes), idempotent, isolated, non-fatal, and
backward-compatible. Adversarial review confirmed the central per-issue claim and surfaced one MAJOR in the
secondary `audit_history` artifact — fixed (per-issue filtering + per-`dataset_id` cap) — plus a MINOR
footgun, both with no single-issue behavior change. **Offline-certified.** Remaining gates: merge → deploy
(`git pull` + restart) → run `--all` → post the "ready to re-intake" signal so Johnny re-runs intake and
confirms `promises` + `i_ride_for_them` Review Records appear (the live cert).
