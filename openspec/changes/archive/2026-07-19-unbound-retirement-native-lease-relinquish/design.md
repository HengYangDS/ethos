## Context

The existing exceptional route correctly blocks an active lease, but a source
holder may retain a valid exact lease after its worktree has disappeared. The
current command cannot reach its own required postcondition
`active_lease_absent` without bypassing its native lifecycle.

## Design

After the ordinary exact-target, accepted-Chronicle, Claim, protected-ref, and
explicit-control checks succeed, the command may relinquish one lease only when
its holder is `ETHOS_ACTOR`, its lease ID, epoch, and expected head are the
freshly observed values, and that head equals the target ref. It uses the
existing generation-bound `revoke_lease` CAS. It then reobserves stable
retirement bindings before `git update-ref -d`; any drift leaves the ref intact.
A lease release is not authority: a missing, foreign, mismatched, or stale lease
still blocks the same command.

## Alternatives

- **Wait for expiry:** leaves a long, avoidable local deadlock and cannot
  establish a contemporaneous native lifecycle receipt.
- **Manual lease deletion:** violates the command boundary and loses exact CAS
  evidence.
- **Relax all active-lease checks:** would allow foreign lease takeover.

## Proof Strategy

Run focused exceptional-retirement tests for matching-holder success, foreign
lease blocking, ref-delete failure after relinquishment, and observation drift;
then strict OpenSpec lifecycle, exact-HEAD proof, candidate land, and local
accepted closeout. The final target retirement remains a separate command.
