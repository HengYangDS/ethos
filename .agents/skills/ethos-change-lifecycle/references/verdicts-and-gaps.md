# Verdict & Gap Reference — ETHOS Change Lifecycle

Skill-specific quick reference for reading the loop's JSON verdicts and acting on
common `required_gaps`. This is a lens over the command plane — the live command JSON
and `system/evidence_boundaries.toml` remain authoritative if they disagree.

## Reading a verdict

Every loop command emits the same envelope:

| field | meaning |
| --- | --- |
| `verdict` | closed state: `pass`, `block`, or `unknown`; only `pass` authorizes an effect |
| `state` | one word: `ready` / `proven` / `blocked` / `dry_run` / `clean` / `gapped` |
| `required_gaps` | the exact blockers; each names what to resolve |
| `next_actions` | the next command to run |

A mutation command (`land --apply`, `publish --apply`) with `verdict=block` or
`verdict=unknown` exits NON-ZERO — the stop is enforced, not advisory. `status`, `plan`, and dry-run
`prove` report gaps without creating a second reader command.

## Common gaps → what they mean → next action

| gap (prefix) | meaning | next action |
| --- | --- | --- |
| `protected_root_mutation` | you tried to mutate an accepted/candidate/release root directly | move to a work lane (`ethos lane start`) and edit there |
| `work_lane_dirty` | the work lane has uncommitted changes | commit the bounded Work Lane change or deliberately revert/absorb the residue through a governed lane; do not use stash as the carrier |
| `protected_root_mutation` | accepted/candidate/release root has tracked dirty work | stop normal work; classify the pollution; absorb useful work into an owned Work Lane with evidence or revert useless/unsafe pollution from the protected root; do not stash |
| `authorization_required` | `land/publish --apply` without `--authorize` | add `--authorize` once you intend the mutation |
| `expect_head_required` / `expect_head_mismatch` | missing or stale `--expect-head` | pass `--expect-head "$(git rev-parse HEAD)"` |
| `proof_not_proven` | no executed proof bound to the current HEAD | run `ethos prove --execute --expect-head "$(git rev-parse HEAD)"` first |
| `candidate_base_stale` | the candidate moved since your lane branched | `ethos lane refresh-base`, then re-land |
| `hook_admission_*` | a tracked write did not pass write admission | run `ethos lane prewrite <paths>` (arm hooks via `ethos hook install` / adopt) |

## Evidence boundaries (never conflate)

- dry-run readiness `!=` executed proof — only `prove --execute` mints HEAD-bound proof
- digest-bound `!=` semantic correctness
- local evidence `!=` hosted verification
- promotion `!=` absolute correctness (only: a bounded claim was admitted)

## The stop line

`publish` reports LOCAL publication readiness. Remote push is a deferred, separately
human-authorized step. Stop before it — never push as part of the loop.
