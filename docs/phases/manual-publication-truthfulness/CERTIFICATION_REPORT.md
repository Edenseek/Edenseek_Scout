# Certification Report — Manual-Publication Truthfulness (F1 severity + F2/F3/F4 UI)

**Track:** Dashboard truthfulness (SXI-2a live-drive findings) · **Branch:** `week12-manual-truthfulness-hotfix`
**Date:** 2026-08-12 · **Discipline:** certified-first (build → adversarial review → certify → deploy → verify)
**Status:** CODE-COMPLETE · adversarially reviewed (1 round + fold) · offline-certified · HELD for merge → deploy → re-audit

---

## 1. What changed and why

Driving SXI-2a on prod, Johnny surfaced three findings with one root cause: **Scout renders
`applicability: "manual"` / a not-yet-platform-approved state as if it were "not good" (FAIL) or "not yet"
(waiting).** Johnny then diagnosed the FAIL precisely (bridge
`2026-08-12_publisher_F1_answer_evidence_loaded_platform_approval_absent_by_design.md`):

- `worst_severity = FAIL` came from `evidence.loaded` flagging `platform_approval.json` as "not read".
- But `platform_approval` is a **separate authority** — under the ratified Creator · Publisher · Edenseek
  Platform model, platform approval is a human act performed **after** publication; a publish must never
  write it. So it is **correctly absent** on every not-yet-platform-approved revision (nothing has been
  platform-approved since 2026-08-02, which is exactly when the FAIL streak began).
- **The finding is right; the severity is wrong.** Scout read everything that *exists* — 3/4 with
  `platform_approval` absent *is* the complete evidence set for a creator-approved revision. Johnny's
  explicit ask: **do not mask it — reclassify** it to a truthful non-FAIL signal.

## 2. Changes

**F1 — evaluation-layer severity (`audit_review.py`, `EVALUATION_VERSION v1→v2`):**
- `_REQUIRED_EVIDENCE_ROLES = (approved_pointer, processing_snapshot, review_report)`. `evidence.loaded`
  FAILs only when a **required** object could not be read — `platform_approval` is no longer counted.
- New `platform.approval` finding maps the probe status exhaustively: `read`→PASS, `missing`→**WARNING**
  ("not platform approved" — a workflow state), `denied`/`error`→**FAIL** (exists-but-unreadable is a real
  evidence problem, distinct from absent).
- No masking: a genuinely broken audit (unreadable pointer/snapshot/review_report, or an adapter rejection)
  still FAILs. `platform.approval` PASS suppresses nothing.

**F2 — UI (`static/index.html`):** both analytical tables show `series · issue` (via `issueLabel`), matching
the picker — the bare `issue_001` distinguished nothing.

**F3 — UI:** geometry/metadata empty states say *"Not applicable — this is a manual publication (no
generated side)…"* for `applicability: manual`, instead of *"appears once a v2 audit has run"* (which told
the publisher to wait for something that never arrives). Generated publications keep the old text
byte-identically.

**F4 — UI (the "can't see findings" gap):** new `findingsPanel(rep)` on the Intelligence analysis view
surfaces the selected report's findings (code / severity / title / detail), severity-ordered — so a reader
(human or AI agent) can see **why** a report has its severity. XSS-safe (all report-controlled fields
`esc`'d).

## 3. Version / comparability / idempotency (F1)

`evaluation_version` is in **both** the comparability axis (`scout_report_index` `METADATA_AXES`) **and** the
ledger fingerprint (`scout_delta_audit.static_versions`). v1→v2 therefore (a) changes the fingerprint → a
re-audit **runs** (no "already processed" skip), (b) mints a distinct ledger key + comparability key → no
collision, and (c) does not mutate existing immutable v1 reports (they keep `evaluation_version: "v1"` and
their old severity). A re-audit after deploy regenerates current revisions under v2 — the spurious FAILs
become WARNINGs. Equivalently, platform-approving a revision writes `platform_approval.json` → the WARNING
clears to PASS on its own.

## 4. Tests

Full suite **467 passed** (+2). New in `tests/test_audit_review.py`:
`test_absent_platform_approval_is_warning_not_evidence_fail` (missing → evidence.loaded PASS +
platform.approval WARNING + no FAIL), `test_denied_platform_approval_is_a_real_read_failure` (denied →
platform.approval FAIL); happy-path extended to assert `platform.approval` PASS. `_view`/`_fake_client`
gained `missing_keys`/`denied_keys`. Dashboard JS `node --check` clean.

## 5. Adversarial review (one round + fold)

**Verdict: safe to merge + deploy — no MAJOR/MINOR-severity defects in the logic.** The reviewer verified
the reclassification masks no real evidence failure (exhaustive probe-status mapping; required objects still
FAIL), the v1→v2 bump is correct on re-audit / boundary / no-retro-mutation (no hardcoded `=="v1"`), and F4
is XSS-safe with sound null guards. Two MINOR items were folded:

| # | Sev | Finding | Resolution |
|---|-----|---------|------------|
| 1 | MINOR | F4 `findingsPanel` `<li>` had two direct children under the `.att li` `70px 1fr` grid → badge+title crammed into the 70px column. | **Fixed** — restructured to the `.att` convention (bare `sev` span first, wrapper `<div>` second); added the missing `.att li.PASS` accent. |
| 2 | MINOR (latent) | `manifest.summary.audit_ready`/`objects_missing` still count `platform_approval` as missing → now disagree with the v2 findings. | **Documented follow-up (§6).** No current consumer renders these fields (verified), so no user-visible contradiction; deferred rather than expand this hotfix into the manifest-summary semantics. |

NIT (pre-existing, not introduced): `evaluation_version` is a `METADATA_AXES` axis but not `GEOMETRY_AXES`,
so a v1→v2 transition marks a metadata boundary but not a geometry one. Noted for awareness.

## 6. Documented follow-ups

- **`audit_ready`/`objects_missing` required-scoping:** make the manifest summary consistent with the v2
  finding rules (platform_approval optional), so a future consumer can't read `audit_ready=False` as a gate
  on a healthy creator-approved revision. Latent (no consumer today); its own small change.
- **spread_order reading-order axis:** the published `spread_order` (society_of_killers `rev_08bf114d`) is a
  manual publication → it won't arrive through the delta family; the axis must read it from the published
  approved geometry directly (base64 inside `processing_snapshot.json → artifacts[] → approved_geometry.json`).
  Separate track.

## 7. Certification statement

Additive and read-only on the UI; the evaluation-rule change is a **truthful reclassification** (not a mask)
that reserves `evidence.loaded` FAIL for evidence that should exist and could not be read, cleanly versioned
via `EVALUATION_VERSION v2` in both the comparability axis and the ledger fingerprint. Adversarial review
found no logic defect; the two MINORs are fixed / documented. Suite **467 passed**, JS clean.
**Offline-certified.** Remaining gates: merge → deploy (`git pull` + restart) → re-audit (`--all`) so current
revisions regenerate under v2 and the spurious FAILs clear → verify the findings viewer renders.
