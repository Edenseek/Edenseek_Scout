# Certification Report — SXI-2a (multi-issue dashboard: issue picker + issue-scoped report views)

**Track:** Scout Expansion Increment 2 · sub-increment **2a** (the §2 reachability fix)
**Branch:** `week12-sxi2a-issue-picker`
**Date:** 2026-08-12
**Discipline:** certified-first (build → adversarial review → certify → deploy → verify, each separate)
**Status:** CODE-COMPLETE · adversarially reviewed · offline-certified · HELD for merge → deploy
**Authorization:** founder-authorized (Derek) ahead of the full SXI-2 Keystone approval — he was blocked
live on viewing the `i_ride_for_them` report from Engineering/Intelligence. The remaining SXI-2 sub-
increments (2b–2e) stay gated on the bridge approval.

---

## 1. What changed and why

Johnny's dashboard walkthrough (§2) found that Increment 1's multi-issue audit was invisible from the
analytical views: `/audit-review/archive`, `/reports/latest`, and `/reports/{report_id}` all read the
**single env-configured issue's** index (`SCOUT_REPO_S3_PREFIX` = `society_of_killers`), so a
newly-published issue (`i_ride_for_them`) had **no UI path** — its report was neither in the selector nor
fetchable by id. SXI-2a makes the analytical views selectable per discovered issue.

This is pure **surfacing over already-certified machinery** (P2): Discovery already enumerates every issue,
the Registry already spans them, and each issue already has its own persisted index. Scout stays
read-and-advise — every new endpoint is a GET projection over persisted Scout artifacts; no Publisher
writes, no new contract.

## 2. Server-side changes

- **`scout_discovery.context_for_prefix(issue_prefix, *, env=None)`** (new) — reconstructs ONE issue's
  `IssueContext` from its prefix WITHOUT re-listing S3: the approved surface is always `{issue}/approved`
  and buckets/regions are shared config — the identical construction `discover_contexts` uses per issue,
  minus the enumeration. Raises `IssueContextError` (malformed prefix) / `ScoutDiscoveryError`
  (unconfigured). A regression test asserts it equals the context `discover_contexts` builds for the same
  prefix, so a scoped read hits exactly the surface Discovery/Registry would.
- **`GET /issues`** (new, `app.py`) — enumerates discovered published issues via `discover_contexts()`,
  projecting `{issue_prefix, publisher_id, title_group_id, series_id, issue_id}` per issue for the picker.
  Discovery/config failure → 503.
- **`app._issue_context(issue_prefix)`** (new helper) — resolves a selected prefix to a context, or `None`
  for the env default (unchanged behavior). Translates `IssueContextError` → **400** (client error);
  config errors propagate to the endpoint's 503 handler.
- **`/audit-review/archive`, `/audit-review/search`, `/reports/latest`, `/reports/{report_id}`** — each
  gained an optional `issue_prefix` query param scoping the read (via `_issue_context`). Empty = configured
  default (byte-identical to prior behavior). Each endpoint re-raises `HTTPException` before its broad
  `except`, so the 400 is not swallowed into a 503.

## 3. Front-end changes (`static/index.html`)

- New state `selectedIssuePrefix` (null = configured default) + `issues` cache.
- `issueQS(sep)` appends `?issue_prefix=` / `&issue_prefix=` only when an issue is selected; `loadIssues()`
  fetches `/issues`; `loadArchive()`, `loadSelectedReport()`, and the search call are scoped through it.
- `reportBar()` renders an **Issue** `<select>` — shown ONLY when Discovery finds more than one issue, so a
  single-issue deployment is visually unchanged. Options labelled `series · issue` (title-group hierarchy is
  SXI-2b).
- `onPickIssue()` sets the prefix, resets the report selection to that issue's latest, clears caches, and
  re-renders. The identity strip already reads the selected report's `issue_identity`, so it reflects the
  chosen issue automatically.

## 4. Backward compatibility

With no `issue_prefix`, `_issue_context` returns `None` and every endpoint behaves exactly as before
(env-configured issue). The front-end picker is hidden on a single-issue deployment. No existing caller of
the four endpoints passes the new param; the added query param is optional with an empty default.

## 5. Boundary / safety

Read-only throughout. The one adversarial surface is `issue_prefix` (user-supplied → S3 prefix): it is
validated by `IssueContext.for_prefixes` → `_normalize_scout_prefix`, which requires a well-formed
`publishers/.../issues/{id}` ownership chain and rejects anything else with `IssueContextError` (→ 400).
Buckets/regions come from shared config, not the request, so a crafted prefix cannot redirect the read to
another bucket. (Confirmed under adversarial review — see §7.)

## 6. Tests

Full suite **465 passed** (+12). New: `tests/test_issues_endpoint.py` (auth, issue projection, discovery
failure→503, archive/report scoping passes the resolved context, malformed prefix→400 not 503, no-param→
context None) and `TestContextForPrefix` in `tests/test_scout_discovery.py` (identity/prefix
reconstruction, equals `discover_contexts` construction, malformed→`IssueContextError`,
unconfigured→`ScoutDiscoveryError`). Dashboard JS `node --check` clean.

## 7. Adversarial review (one round + verification)

**Verdict: safe to merge + deploy — no security or correctness defects.** The reviewer read the diff plus
downstream consumers and tried hard to break the one adversarial surface (`issue_prefix`).

Claims the reviewer tried and could NOT break:
- **No cross-bucket / SSRF.** Bucket + region come only from `_config(env)`; the request steers only the
  key *prefix*. Unreachable.
- **Path traversal neutralized.** A crafted `publishers/../../etc/...` prefix passes chain validation but is
  sent to S3 as a literal key (flat keyspace, `..` is a literal component) → `NoSuchKey` → `_empty_index`.
  No data escapes.
- **No arbitrary-object read.** `/reports/{id}` reads the fixed `{prefix}/reports/report_index.json`, then
  the body from the server-controlled `entry.persisted_key.history` — never a request-supplied key.
- **Region/bucket scoping correct.** All issues share the `edenseek-scout` bucket; `context_for_prefix`
  derives `scout_region` from the same env var, so the body read's `SCOUT_REPO_S3_REGION` never mismatches.
- **400-vs-503 correct.** `IssueContextError` → 400 (arg evaluated inside the `try`, re-raised by
  `except HTTPException: raise` before the broad `except`); `ScoutDiscoveryError` (unconfigured) → 503.
- **Regression clean.** No-param → `context=None` → env default, byte-identical; no internal caller uses the
  HTTP signature; `build_archive(context=)` scopes both the index and the failed-run ledger.

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MINOR | `loadArchive()` became issue-scoped via a shared global, and Operations → "Scout health" (`opsHealth`) also read it — so picking an issue in Engineering/Intelligence would silently scope that Ops panel, where no picker is shown, while the publisher-wide Publisher Health panel did not follow (two Ops panels disagree, no cue). | **Fixed.** Added a separate unscoped `loadOpsArchive()` (+ `opsArchive` cache, cleared in `resetReportCaches`); `opsHealth` now uses it, so Operations stays on the configured issue exactly as before SXI-2a. Only the analysis views follow the picker. |
| 2 | NIT | Single-issue case injects an empty `${issuePicker}` text node — visually identical, not byte-identical. | Accepted (whitespace only). |
| 3 | NIT | `issueQS` sep handling. | Verified correct (`?` default; search uses `&`). |

## 8. Certification statement

The change is additive, backward-compatible (byte-identical with no `issue_prefix`; Operations unchanged
after the §7-#1 fix), read-only, validates the one user-supplied prefix before use, and surfaces
already-certified multi-issue machinery rather than adding business logic. Adversarial review found no
security/correctness defect; the one MINOR UX-coupling is fixed and JS re-verified. Suite **465 passed**,
JS `node --check` clean. **Offline-certified.** Remaining gates: merge → deploy (`git pull` + restart) →
verify the picker lists both issues and the `i_ride_for_them` run_seq 1 report renders.
