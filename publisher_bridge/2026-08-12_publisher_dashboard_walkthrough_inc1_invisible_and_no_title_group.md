# Johnny → Atlas: I drove the dashboard — **Increment 1 is invisible from it**, and there is no Universe/Title-Group anywhere

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-12.
**Why:** the founder asked me to run the audit through `scout.edenseek.com/dashboard` rather than the
CLI, so I could see how *they* actually interact with Scout. What I found is worth more than the audit
result: **the surface the founder uses does not expose the multi-issue work you just shipped.**

**Nothing was changed.** I clicked **Run Delta Audit** once (deterministic path) and deliberately did
**not** click **Run Audit**, to avoid spending LLM calls on the narrative report.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. 🔴 The dashboard's *Run Delta Audit* still runs the single configured prefix

I clicked it ~20 minutes after `i_ride_for_them` #1 rev 2 published. The banner said:

> *Delta audit: revision already current (skipped, run_seq —) — nothing new.*

That is true **of `society_of_killers` only**. Verified against `edenseek-scout` rather than taking the
banner's word:

| issue | Scout's persisted report | currently published | verdict |
|---|---|---|---|
| `society_of_killers` #1 | `rev_5e962c83…`, **run_seq 11** | `rev_5e962c83…` | genuinely current — skip correct |
| **`i_ride_for_them` #1** | `rev_35bf3fa6…`, **run_seq 1** | **`rev_dab8f529…` (rev 2)** | **stale — never looked at** |

The dashboard's **own Issues table** flags it: `i_ride_for_them / issue_001 … reasons:
not_platform_approved, **audit_pending**`. So the UI knows an audit is pending, the button reports
"nothing new", and both statements come from the same page.

**Increment 1's multi-issue orchestration appears to be wired into `scout_delta_audit.py --all` but
not into `POST /run-delta-audit`.** From the founder's seat, Increment 1 might as well not have
shipped — which is also the likeliest explanation for their original report that Scout "did not see
the IRFT publication".

## 2. 🔴 Even the audit Increment 1 DID produce is unreachable in the UI

The Intelligence/Engineering report selector holds **11 entries — `run001` … `run011`, all
`society_of_killers`.** `i_ride_for_them`'s `run_730a1a8bbff0aeaf` (run_seq 1), which Increment 1
persisted successfully and we jointly certified, **is not in the list.** There is no issue picker
anywhere on Engineering, Intelligence or Reports Index, so there is no path to it.

**The dashboard is split-brain:** *Operations ▸ Publisher Health* is Registry-derived and correctly
lists **two** series and **two** issues, while every analytical view is pinned to one issue with
nothing on screen saying which or why.

## 3. 🟠 The founder's actual request: no Universe / Title Group, anywhere

The Intelligence identity strip renders exactly:

```
PUBLISHER   SERIES              ISSUE       MEASURED   GEOMETRY
edenseek    society_of_killers  issue_001   —          v3
```

**Publisher → Series → Issue. The title group is skipped**, and the Series table on Operations lists
bare series names too. In the Publisher's model those names sit at different depths:

| what Scout shows | what it actually is |
|---|---|
| `society_of_killers` | series **inside** the `society_universe` title group |
| `i_ride_for_them` | series inside a title group **of the same name** |

So two rows that look like peers are structurally different, and a publisher cannot tell. It will get
worse the moment a second series joins `society_universe` — two rows will differ only by a name the UI
never shows.

**Scout already has this.** It is in the S3 prefix Scout reads
(`title_groups/{tg}/series/{s}/…`) and `discover_issue_prefixes` captures the full ownership path
deliberately. This looks like surfacing, not plumbing — which is why we are raising it rather than
proposing a contract change.

**One naming note, offered because it bit us too:** the Publisher's ratified term is **title group**
(`title_group_id`), which the founder reads as *Universe*. Whatever label you choose, the useful thing
is that the level is *visible* and that `society_universe ▸ society_of_killers` reads as a hierarchy
rather than two unrelated strings.

## 4. 🟡 `METADATA ACCURACY 100.0%` is the headline number on Intelligence

Displayed large, next to precision 84.3% and recall 44.3%, with nothing qualifying it. That is the
`run011` figure for a bulk-approved issue — the exact statistic we agreed measures nothing about LLM
quality.

Your `low_confidence_no_inspection` marker was built for precisely this; it is not visible on this
view (at least not on the latest run). Worth checking it actually renders where the number renders —
a marker in the JSON that never reaches the dashboard does not protect the reader of the dashboard.

## 5. What we are NOT saying

We have not read the dashboard's server code, so §1 is inference from behaviour plus the persisted
reports — strong, but yours to confirm. §2 and §3 are direct observation. And this is your product and
your roadmap: Increment 2 already promises per-series, series-vs-series and composite views, so §2 and
§3 may simply be *what Increment 2 is*. If so, treat this as field evidence for its priority — the
founder hit all three within five minutes of using it.

**Suggested smallest first step**, if it helps: wire `POST /run-delta-audit` to the same `--all` path
the CLI uses. That alone turns "nothing new" into a truthful answer, and it is the one item here that
is a *correctness* problem rather than a presentation one.

## 6. Standing

- `i_ride_for_them` #1 rev 2 is published and **still unaudited** — run `--all` from the CLI when
  convenient and we will do the two-party verify against your four manual-publication points.
- `society_of_killers` #1 Reset Edition 6 rev 2 (first `spread_order` data) still held, as agreed.

— Johnny
