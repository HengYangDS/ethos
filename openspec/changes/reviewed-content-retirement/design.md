## Context

The existing operation orders worktree removal, ref CAS and Lease revocation.
Its durable request and progress receipts already recover partial completion.
Clean ancestor retirement remains the inexpensive default. The missing input
is not another lifecycle state: it is a reviewed destructive content preimage.

## Decisions

1. Extend `lane retire abandon` with an explicit reviewed-content derivation
   input. Derivation observes, but does not delete. Application requires the
   exact derived receipt, its digest, current actor and authorization.
2. Bind index entries and filesystem identity/content, including ignored files
   and literal symbolic-link targets without following them. Reject unknown
   node types, root/index links, junctions, nested repositories, conflicts and
   unstable observations. No user material is made disposable by an ignore rule.
3. Keep semantic adjudication explicit in the existing reason: accepted source
   and current owner references explain absorption, supersession or rejection.
   Inventory identity proves which bytes are selected, not that their meaning
   is accepted. The final operator reviews the derived inventory before apply.
4. Use the existing retirement operation, plan, lock, native worktree effect and
   recover command. Preflight and effect-time checks reject changed content,
   moved refs, changed Lease generation, locked worktrees or active consumers.
   No normal clean path gains unconditional force removal.
   Reviewed historical disposal uses current coordination: a missing or expired
   Lease requires no resurrection, a valid Lease requires its holder, and a new
   Lease invalidates the reviewed operation. The Git effect binds one nonzero
   topic preimage to deletion, with the accepted ref asserted and the current
   actor equal to the receipt actor. Historical absence of an adoption profile
   does not prevent that deletion from the valid accepted control checkout.
   Lock contention returns promptly with `lane_retirement_in_progress`, the
   unchanged request identity and its existing recovery command. Until lock
   acquisition permits observation, the result omits progress and effect claims.
   Recovery after normal holder exit or process death reacquires coordination
   and rechecks current facts; it never deletes the lock to steal ownership.
   This lock coordinates retirement calls, not arbitrary filesystem writers.
   All actual writers must first finish or stop and honor lane coordination
   through disposal. The operator verifies that handoff before content review;
   an empty process observation or changed Lease alone is insufficient. This
   cooperative boundary excludes uncooperative same-UID filesystem writes;
   observed drift, active consumers and unknown liveness still block.
   Ref deletion still consumes the existing short-lived Git transaction intent.
   Its reclamation must compare the complete selected record after acquiring its
   existing lock: unchanged identity alone does not authorize deleting a record
   whose expiry or transaction phase has advanced. This is a dependency of the
   admitted ref effect, not another retirement state or historical intent store.
   Every intent mutation, including clear, uses one stable native-backed lock
   per intent directory. Contention retains the public bounded timeout; process
   death releases ownership without a marker scavenger. Unsupported native
   locking fails closed. The lock is retained rather than unlinked at release,
   and its count is independent of transaction history. This does not change
   intent-directory placement or authorize concurrent old-runtime writers.
5. Read-only generated directories must not prevent removal of an otherwise
   admitted isolated root. Permission handling never follows a link or changes
   shared file inodes. Partial deletion remains visible and recovery cannot
   delete newly added or modified content under the old receipt.

## Alternatives

- Recreate old lanes or copy them under preserve: rejected because it retains
  superseded authority and delays physical retirement.
- Add a separate disposal command/state machine: rejected because the existing
  abandonment and recovery owners already represent the effect and evidence.
- Treat Git ancestry or ignored status as content acceptance: rejected because
  neither accounts for staged, unstaged, untracked or ignored user bytes.

## Validation

Use real small Git repositories for the public path and share fixture setup.
Cover reviewed absorbed and divergent topics, clean-path non-regression,
content/index/actor/Lease/ref drift, links and conflicts, ignored/read-only
resources, interrupted removal, recovery without replay and exact negative
postconditions. Run focused tests before the full frozen proof. Keep product
and tests independently under 40000 ELOC and combined coverage at least 95%.
