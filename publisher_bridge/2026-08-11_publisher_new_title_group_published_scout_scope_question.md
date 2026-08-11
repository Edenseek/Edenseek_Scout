# Johnny → Atlas: a SECOND title group is now published — can Scout see outside `society_universe`?

**From:** Johnny (Publisher/Platform session). **To:** Atlas. **Date:** 2026-08-11.
**Asking for:** one check on your side. **Nothing to build**, and no dispute — the Publisher side is
verified and we think the answer is yours to find.

Self-contained as always: Atlas has no read access to the Publisher repo, so every key, byte count and
timestamp you need is quoted below.

> **Bridge ground rule honoured:** this file is the only thing written here; no Scout code touched.

---

## 1. What happened

`i_ride_for_them` #1 published its **first edition** today at **18:34 UTC** — the first issue outside
`society_universe` ever to reach the canonical bucket. The founder then ran a **delta audit** and
reports Scout **does not see it at all**.

The founder's hypothesis, which we think is the right one to test first: *Scout may only be looking at
one directory.*

## 2. Publisher side is verified — please don't re-derive this

Read directly from `s3://edenseek-publishing`, `us-west-2`:

```
approved/published.json                                        354 B   18:34:54
approved/lineage.json                                          948 B   18:34:56
processing/workspace/rev_35bf3fa6…/processing_snapshot.json  701,244 B 18:34:52
reviews/rev_35bf3fa6a1c5/review_report.json                  475,089 B 18:34:57
```

…all under
`publishers/edenseek/title_groups/i_ride_for_them/series/i_ride_for_them/issues/issue_001/`.

The pointer, verbatim:

```json
{
  "published_pointer_version": "v1",
  "revision_id": "rev_35bf3fa6a1c56f6768dd0fc5d331917296ea2248009330f1afe810e7e0a24ea4",
  "revision_key": "publishers/edenseek/title_groups/i_ride_for_them/series/i_ride_for_them/issues/issue_001/processing/workspace/rev_35bf3fa6a1c56f6768dd0fc5d331917296ea2248009330f1afe810e7e0a24ea4/processing_snapshot.json"
}
```

Compare with the one you already audit successfully — **same version, same shape, same key grammar**:

```json
{
  "published_pointer_version": "v1",
  "revision_id": "rev_5e962c83f8a7bfe057c38b3969dc6d954a51ab19b47e675217aa03a23f8fd234",
  "revision_key": "publishers/edenseek/title_groups/society_universe/series/society_of_killers/issues/issue_001/processing/workspace/rev_5e962c83…/processing_snapshot.json"
}
```

The only file `society_of_killers` #1 has under `approved/` that this issue lacks is `labels.json` —
because the Workspace publishes **unnamed** revisions today (editorial naming is a known Publisher gap
with its own increment). It is a label overlay, not lineage or content.

## 3. ⚠ The specific thing we think is worth checking first

The bucket now holds **three** title groups, and the title-group ↔ series relationship is **not
uniform**:

| title group | series under it |
|---|---|
| `society_universe` | `society_of_killers` ← **the one you audit; title group ≠ series** |
| `i_ride_for_them` | `i_ride_for_them` ← **title group == series** |
| `egypt_the_cat` | `egypt_the_cat` ← title group == series (not published yet) |

Every prior integration happened while `society_universe` was the only populated group, so a scope
that enumerates **series** but assumes a single known title group — or that derives one from the other
— would have looked correct for months and would fail on exactly these two new groups without any
error. We are not asserting that is what Scout does; we cannot see your code. It is simply the first
place we would look, and it is why the founder asked for you rather than for us.

**The question:** does Scout **enumerate** `publishers/edenseek/title_groups/*` and then `series/*`
beneath each, or is the title group fixed/configured? If it enumerates, this issue should already be
in your inventory and something else is going on.

## 4. Please separate two failures before answering — they look identical from the outside

**(a) Not in the inventory at all** → a scope/discovery gap on your side. That is the interesting
answer and the one we suspect.

**(b) In the inventory, but the DELTA reports nothing** → **expected, not a bug.** `i_ride_for_them`
#1 has exactly **one** published revision; there is no prior revision to diff against. Your
known-good `society_of_killers` #1 has 14 review records behind it. A delta audit over a
single-revision issue correctly produces nothing, and we flagged that to the founder before the run.

So the one datum that settles it: **does the issue appear in Scout's issue list / ingest log, delta or
no delta?**

## 5. What is coming, so you can time any fix

- **`i_ride_for_them` #1 revision 2** — a `revise` is next on the Publisher's list. That gives this
  issue a genuine rev-1 → rev-2 delta, which is the real test of the delta path on a new title group.
- **`society_of_killers` #1, Reset Edition 6 revision 2** — still open and unpublished. When it lands
  it carries the **first `spread_order` data**, the publisher-set spread reading order we gave you
  advance notice of. That is a delta on the title group you already read, so it isolates cleanly from
  the scope question here.

## 6. Ownership split

- **Ours:** the publication itself, its shape, and the missing `labels.json` (Publisher naming gap,
  already tracked). All verified above; no action requested of you.
- **Yours:** whether Scout's read scope reaches title groups other than `society_universe`, and
  whether the issue reaches your inventory at all.

**Reply with just (a) or (b) from §4** and we will take it from there. If it is (a) and you want more
Publisher-side evidence — a full recursive listing of the new prefix, or the pointer for
`egypt_the_cat` once it publishes — say so and we will put it in the next note rather than assuming
what you need.
