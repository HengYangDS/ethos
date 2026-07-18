# Design

## Decision

`release_mirror` is an explicit branch-role policy with two values:
`independent` (default) and `accepted_ff`. The committed candidate tree is the
policy source for a release-ref move, so a closeout and hook evaluate the same
configuration even while linked accepted and release worktrees still expose an
older checkout.

For `accepted_ff`, closeout first verifies that release is an ancestor of
accepted. It writes distinct one-shot intents for `dev` and `main`, carries the
candidate proof to accepted state, then uses one `git update-ref --stdin`
transaction to compare-and-swap both refs to the candidate head. Both refs are
therefore unchanged on a failed transaction. Afterward the accepted worktree
and any linked release worktree are hard-reset to the promoted head and checked
clean; failures return structured gaps.

## Failure boundaries

- A raw `main` move lacks its exact intent and is blocked.
- A release branch ahead of or diverged from accepted is blocked before ref
  mutation.
- A missing or invalid candidate proof is blocked by existing closeout
  admission.
- A sync failure is visible as a structured post-transaction failure; no raw
  recovery or ref rewrite is attempted.

## Compatibility

No repository changes behavior until it explicitly sets
`release_mirror = "accepted_ff"`. Existing independent release policy and
accepted closeout remain unchanged.
