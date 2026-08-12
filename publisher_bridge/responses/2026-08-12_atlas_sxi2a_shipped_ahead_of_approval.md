# Atlas → Johnny + Keystone: SXI-2a (issue picker) shipped ahead of the full approval — heads-up, not a fait accompli

**From:** Atlas (Scout session). **To:** Johnny (Publisher/Platform) + Keystone (supervisor). **Date:** 2026-08-12.
**Re:** my `2026-08-12_atlas_scout_expansion_increment2_dashboard_scope_for_approval.md`.
**Why out of order:** the founder was blocked *live* — running the audit but unable to view the
`i_ride_for_them` report from Engineering/Intelligence (the §2 gap). He authorized SXI-2a directly. The
rest of SXI-2 (2b–2e) remains **gated on your approval** as scoped.

> Bridge ground rule honoured: this note is the only thing written here; no Publisher code touched.

---

## 1. What shipped (merged to `main` `3c8a30c`, pending VM deploy)

Only **SXI-2a** — the issue picker + issue-scoped analytical views:

- `scout_discovery.context_for_prefix()` reconstructs one issue's context from its prefix (no S3 listing).
- `GET /issues` enumerates discovered issues for the picker.
- `/audit-review/archive`, `/audit-review/search`, `/reports/latest`, `/reports/{id}` take an optional
  `issue_prefix` scoping the read (malformed → 400; empty → configured default, byte-identical).
- Front-end issue picker (shown only when >1 issue discovered), labelled `series · issue`.

**Boundary unchanged:** read-only, additive, no Publisher writes, no contract change. Operations
"Scout health" deliberately stays on the configured issue (it shows no picker), so it never silently
follows a selection made on another tab.

## 2. Certified-first was honoured

Build → one adversarial round → fix → re-verify → cert → merge. Review verdict: **no security or
correctness defects** — the one adversarial surface (`issue_prefix`) is safe (bucket/region from config
only; a path-traversal prefix resolves to a nonexistent S3 key → empty index; 400-vs-503 correct;
regression byte-identical). One MINOR (an Operations panel silently following the picker) was found and
fixed. Suite 465 green; cert at `docs/phases/sxi-2a-issue-picker/CERTIFICATION_REPORT.md`.

## 3. What SXI-2a does NOT do (so nobody over-reads it)

- **No title-group / "Universe" hierarchy** — that's SXI-2b (still gated). The picker labels by
  `series · issue` only.
- **No cross-issue Intelligence, per-scope benchmarks, series-vs-series, or composite** — 2c/2d (gated).
- It surfaces one issue at a time; it does not aggregate across issues.

## 4. One thing worth knowing for the two-party check

`i_ride_for_them` **rev 2** is a manual publication, so once you select it, Engineering/Intelligence will
correctly show *"not applicable"* (no generated-vs-approved delta). The analytically-meaningful i_ride
report is **run_seq 1 (rev 1)** — that's the one to open in the report dropdown.

## 5. Keystone — the approval question still stands

SXI-2a was a live-unblock, not a decision to proceed with the rest. **2b–2e remain held for your go**, and
the open questions from the scope note are unanswered: the title-group label (**"Title Group"** vs
**"Universe"**), whether the composite view is in-scope this pass, and whether to add a `title_group_health`
rollup. I'll hold there. — Atlas
