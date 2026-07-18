## Context

At carrier start, `candidate/dev`, `dev`, and `main` share a clean local head,
while GitLab `submit/dual-remote-reconciliation-20260718` and GitHub
`submit/hosted-proof-receipt-20260718` share `a1b9041f`.  That tip is neither
an ancestor nor descendant of the local head and changes seven CI/proof files.
The existing reconciliation carrier deliberately left later closeout and remote
work outside its historical archive.

## Goals / Non-Goals

**Goals:** retain the submit patch through one normal merge; bind a fresh claim,
OpenSpec scope, Chronicle, executed proof, candidate land, accepted closeout,
and per-ref no-force publication evidence; delete submit refs only after
accepted ancestry proves absorption.

**Non-Goals:** force-push, rebase, reset-based ref movement, stash, deletion of
foreign lanes, release/tag work, or an inference from local proof to hosted CI.

## Decisions

1. Freshly observe submit and protected refs immediately before each effect;
   any changed input invalidates the pending action.
2. Use `git merge --no-ff` for `a1b9041f`; preserve both parents and review
   conflicts rather than replacing history.
3. Treat source/test/template change, local proof, local closeout, remote push,
   remote ref observation, and hosted-provider observation as separate planes.
4. Update protected refs only after their individual normal push dry-runs; use
   no `--force` or rewritten ref.

## Risks / Trade-offs

- A remote moves during work -> re-observe and re-plan before its update.
- A merge conflicts -> stop and retain both parents until an explicit reviewed
  resolution exists.
- Proof or protected push fails -> preserve local state and report the relevant
  plane as unconfirmed; do not delete submit refs.
