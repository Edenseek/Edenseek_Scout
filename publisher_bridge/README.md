# publisher_bridge/ — Publisher ⇄ Scout cross-session channel

A boundary-preserving communication channel between the two Claude sessions:

- **Publisher/Platform session** (works in the `Edenseek` repo) WRITES contract facts, real-shape samples,
  alignment findings, and governance proposals here.
- **Scout session** (works in this `Edenseek_Scout` repo) READS them and WRITES replies under
  `responses/`.

**Why this exists:** Scout does not need read access to the `Edenseek` (Publisher) repository. Instead the
Publisher side — which is the authority on what it emits — deposits exactly what Scout needs here, in
Scout's own repo. This keeps the repository boundary intact (Publisher produces certified evidence; Scout
consumes + verifies) while giving both sides a durable, reviewable record.

**Ground rule:** the Publisher session only ever writes inside `publisher_bridge/`; it does NOT modify
Scout's code. The Scout session owns all Scout-repo code changes. Files here are information + proposals,
not edits to Scout modules.

## Contents

| File | From | Purpose |
|---|---|---|
| `2026-07-27_publisher_alignment_check.md` | Publisher | Alignment check of Scout's 6.3 build vs the *actual* emitted contract — one critical fix + one follow-on risk |
| `real_shape_samples.json` | Publisher | REAL emitted shapes captured from the certified Review Record on production S3 — ground Scout's fixtures on these, not on assumptions |
| `access_grant_proposal.md` | Publisher | D2 — the least-privilege `reviews/` read grant (data-access-contract amendment text + IAM policy) for the founder to provision |
| `responses/` | Scout | Scout writes replies here (template provided) |

## Protocol

1. Publisher deposits findings/samples/proposals (dated files).
2. Scout reads, applies changes in its own repo, and writes a reply in `responses/` (copy the template).
3. The founder relays between sessions; both replies stay in git history as the boundary record.
