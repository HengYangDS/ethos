## Context

On July 18, 2026, the initial carrier was archived after a HEAD-bound local
proof.  Its archived task record intentionally leaves candidate land,
accepted-root closeout, remote updates, and submit retirement incomplete.
Before that work could proceed, `candidate/dev` advanced from
`9541d4c99d8c771cd9beb463efe192ca5ff3f378` to a later independent history,
and both the GitLab `submit/dual-remote-reconciliation-20260718` and GitHub
`submit/hosted-proof-receipt-20260718` refs advanced to
`63b82380098c97f6227c5bec3a900742de8eb7d6`.

## Decisions

1. Preserve the archived carrier as a historical receipt and bind this
   continuation to the same claim.
2. Refresh the owned lane to the live candidate before a new ordinary merge.
3. Re-observe every protected and submit ref immediately before each remote
   effect.  Any move invalidates the pending action.
4. Keep proof, local closeout, remote mutation, remote observation, and hosted
   observation as separate evidence classes.
5. Archive this carrier after the source-level local-convergence proof.  Run
   candidate/accepted closeout and external ref effects only after that archive,
   with fresh observations at every effect boundary.

## Risks

- Candidate or submit movement during the loop requires another refresh or a
  new continuation; no stale proof is reused.
- A merge conflict stops the sequence for reviewed resolution; no history
  rewrite is used.
- Failed proof, closeout, push, or deletion dry-run preserves current state and
  leaves the affected remote ref intact.
