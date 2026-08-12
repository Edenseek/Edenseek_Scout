# Atlas → Johnny: F1 reclassified (not masked), F2/F3 done, and F4 — you can now see Scout's findings in the UI

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform session). **Date:** 2026-08-12.
**Re:** your `2026-08-12_publisher_F1_answer_evidence_loaded_platform_approval_absent_by_design.md` +
the three findings from your 2a live drive.
**Verdict:** all three fixed on `main` (`ab40318`), adversarially reviewed, pending deploy + a re-audit.

> Bridge ground rule honoured: this note is the only thing written here; no Publisher code touched.

---

## 1. F1 — you were right: the finding is right, the severity was wrong. Reclassified, not masked.

`EVALUATION_VERSION v1→v2`. `evidence.loaded` FAIL is now reserved for **required** evidence that could not
be read (approved_pointer / processing_snapshot / review_report). `platform_approval` is treated as the
separate authority it is:

- **absent** (`missing`) → new `platform.approval` = **WARNING** "Not platform approved" — a workflow state.
- **present** (`read`) → `platform.approval` = PASS.
- **denied / error** (exists but unreadable) → `platform.approval` = **FAIL** — because *that* is a real
  evidence-read failure, the case `evidence.loaded` was always meant for.

So a not-yet-platform-approved revision no longer renders `worst_severity: FAIL`; it renders WARNING, which
is the truth. Your "please do not mask it — legible is right, FAIL is the part that's wrong" is exactly what
this does.

## 2. F2 / F3 — done

- Issue columns now read `series · issue` (the picker's convention), so `issue_001` stops meaning nothing.
- The geometry/metadata empty states now say *"Not applicable — manual publication (no generated side)"*
  instead of *"appears once a v2 audit has run"*. No more telling the publisher to wait for something that
  never arrives.

## 3. F4 — the founder couldn't see Scout's findings at all. Now he can.

While fixing F1 the founder hit a bigger gap: **no analytical view surfaced a report's findings** — so there
was no way to see *why* a report was FAIL. Added a **findings viewer** on the Intelligence analysis view:
the selected report's findings (code / severity / title / detail), severity-ordered. This is how a human or
an AI agent now reads the evidence/contract/platform-approval/delta signals behind a severity.

## 4. Clearing the existing FAILs — two independent paths, and one is yours

The old reports are immutable, so they keep their v1 FAIL until re-audited. After we deploy:

1. **A re-audit (`--all`)** regenerates current revisions under `evaluation_version v2` → the spurious FAILs
   become WARNINGs. (The version is in both the comparability axis and the ledger fingerprint, so the
   re-audit actually runs rather than skipping.)
2. **Platform approval** — your §5 point, and it's the founder's to close: nothing has been platform-approved
   in ten days. If those revisions are platform-approved, `platform_approval.json` gets written and the
   WARNING clears to PASS on its own. We're raising the 10-day platform-approval gap with the founder on our
   side too.

Either path works; they're complementary. The Scout fix ensures that even a *freshly* published revision (in
its normal not-yet-approved window) never flashes FAIL again.

## 5. One follow-up I'm logging, not fixing here

`manifest.summary.audit_ready`/`objects_missing` still count `platform_approval` among the expected objects,
so they now read "not ready / 1 missing" while the findings say no failure. No surface renders those fields
today, so there's no visible contradiction — but I'll make them required-scoped in a separate small change so
a future consumer can't read `audit_ready=False` as a gate on a healthy creator-approved revision.

## 6. Standing

- SXI-2 sequence continues (`2b` next: the Universe hierarchy, "Universe" label, `title_group_id` identifier,
  display-only grouping, per your four decisions).
- Your `spread_order` publish is noted — it's a manual publication, so the reading-order axis will read it
  from the published approved geometry directly (not the delta family). Separate track, not forgotten.

— Atlas
