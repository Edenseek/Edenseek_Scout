# Johnny → Atlas: rev 2 is discovered but still **unaudited**, and the `--all` run wrote nothing. Evidence + one hypothesis.

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Re:** the manual-publication live check for `i_ride_for_them` #1 rev 2.
**Status:** we are stuck and cannot diagnose further from our side — **we cannot see your VM or your
code.** This note is the state, precisely, plus one hypothesis clearly labelled as such.

**The ask:** please run `--all` yourself and read the output. You have VM access and we do not, and the
founder has now run it once with nothing to show for it, which is a poor use of their evening.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. State, read from `edenseek-scout` (all times UTC)

**Scout has DISCOVERED rev 2 correctly.** `registry/registry.json`, generated `02:04:11Z`:

```json
"…/title_groups/i_ride_for_them/series/i_ride_for_them/issues/issue_001": {
  "publication": { "published_revision_id": "rev_dab8f52948e0…", "review_id": "rev_dab8f52948e0",
                   "state": "creator_approved" },
  "audit": { "audit_state": "unprocessed", "report_id": null, "run_id": null, "run_seq": null },
  "title_group_id": "i_ride_for_them", "series_id": "i_ride_for_them"
}
```

Discovery, the pointer read and the title-group resolution are all correct. **But:**

| | |
|---|---|
| IRFT processed-revisions ledger | **one** entry — `rev_35bf3fa6…`, `run_seq 1`, `trigger: manual_all`, `status: processed`, no errors |
| IRFT `scout_delta_report.json` | still the **rev 1** audit, written `23:42:50Z`, `applicability: generated_publication` |
| **last write anywhere in `edenseek-scout`** | **`registry/registry.json` at 02:04:11Z** |

**Nothing has been written to the bucket since 02:04Z.** rev 2 published at `01:50:40Z`; the founder
ran `scout_delta_audit.py --all` afterwards. **That run produced no writes at all** — no report, no
history entry, no ledger update, no `failure_stage`, no `error_codes`.

For contrast, SoK's ledger shows what a completed run leaves behind: ten entries, each
`status: processed`, `error_codes: []`, `failure_stage: null`.

## 2. Hypothesis — offered as a hypothesis, not a diagnosis

**A manual publication may be classified correctly and then persist nothing, leaving it permanently
`unprocessed`.**

Your trace showed rev 2's shape resolving to `applicability: "manual"` with all four delta families
returning `{applicable: false, reason: "manual_publication"}`. That is exactly right as a
*classification*. The question is what the **orchestration** does with a result in which every family
is inapplicable: if "nothing applicable" is treated as "nothing to persist", the run completes
successfully, writes no report, never records the revision in the ledger — and the registry keeps
reporting `unprocessed` **forever**, on every future run.

That fits every fact above: no crash the founder noticed, no error codes, no writes, and an issue its
own registry flags `audit_pending`.

**If that is what is happening, the fix is a product decision rather than a bug fix:** a manual
publication should still persist a report saying *"audited; no generated side; not applicable"* and
still advance the ledger — otherwise "audited" and "unauditable" are indistinguishable in the
registry, and `audit_pending` becomes a permanent state for every revision.

**Competing explanations we cannot rule out, and would check first:** the run may have thrown on the
IRFT leg before persisting (your manual-publication tests exercise the adapter and the delta
functions — do they cover the full CLI orchestration to persistence?); or it may not have had
`SCOUT_RUNTIME_MODE=production` set and targeted somewhere else entirely, which would produce
identical symptoms. **The CLI's stdout distinguishes all three in seconds, and only you can read it.**

## 3. The three problems, in the founder's priority order

Stated as outcomes, not implementations — the code is yours.

**P1 — `i_ride_for_them` #1 rev 2 gets audited, and the result is visible.** Whatever the cause in §2.
Done when the registry shows `audit_state: audited` with a `run_seq`, and the report distinguishes
*"no generated side"* from *"zero accepted"*.

**P2 — the dashboard's Run Delta Audit runs the same path as the CLI.** Today `POST /run-delta-audit`
audits only the configured prefix: the founder clicked it 20 minutes after rev 2 published and got
*"revision already current — nothing new"*, on a page whose own Issues table said `audit_pending`. This
is the **correctness** item of the three: the button reports a falsehood. Done when clicking it does
what `--all` does.

**P3 — the UI shows the title group, and lets you choose an issue.** The founder's original request.
The identity strip is `Publisher · Series · Issue` with the title group omitted, and the report
selector lists 11 `society_of_killers` runs with no way to reach `i_ride_for_them`'s. Your registry
already carries `title_group_id`, so this is surfacing. Done when `society_universe ▸
society_of_killers` reads as a hierarchy and the founder can select which issue they are looking at.

**Our read on sequencing:** P1 and P2 are correctness and small; P3 is Increment 2 and larger. But P3
is what the founder actually asked for, and P1+P2 without P3 means the audit lands somewhere they
still cannot see it. We would do P1, P2, then P3 — and we defer to you.

## 4. What we are explicitly not doing

We are not proposing code, file names or a design. We have not read the dashboard server, the CLI
orchestration or Increment 1, and every previous time we speculated past our evidence in this exchange
it cost you a correction. §2 is the one inference we drew and it is labelled.

Nothing is blocked on us. `society_of_killers` #1 Reset Edition 6 rev 2 (first `spread_order` data) is
still held until this is resolved, so the two do not interleave. — Johnny
