## Context

The registered historical failure-matrix worktree is detached. The public
`lane retire abandon --review-content` path returns
`lane_abandonment_branch_invalid`; its contract requires a non-empty branch and
unconditionally derives `delete_ref`. Native worktree removal already accepts
the literal `detached` marker at its adapter boundary. The missing capability is resource
selection and effect derivation, not another deletion engine.

## Decision

Extend the existing abandonment selector with an exact `--path`, mutually
exclusive with `--branch`. A path selects only one registered, non-root,
detached worktree and requires explicit content review. Keep the source root
literal until symlink/junction and registration checks have completed.

Represent an absent branch as absent in the existing operation. Its content
inventory binds the native `.git` marker and index path/identity; fresh Git
observation binds registration, detached HEAD, control common-dir and accepted
OID. A detached operation has only `remove_worktree`: no empty Git transaction,
ref mutation, Lease lookup or invented coordination resource. Ref-bearing
operations retain their exact Git CAS plan and current Lease semantics.

The same preflight and reducer govern application and recovery. Reattaching the
selected worktree, changing its HEAD, registration, index or content, changing
the accepted ref or invocation actor, unknown liveness and active consumption
block removal. Another detached worktree, even at the same commit, is not the
target. Recovery recognizes completed removal without repeating it and rejects
replacement content at the old path.

## Alternatives Rejected

Creating a temporary branch or Lease solely to dispose of a worktree adds
resources with no product meaning. Raw deletion bypasses content/authority
checks. A second housekeeping state machine duplicates the existing receipt,
process observation and recovery protocol. None is required.

## Migration And Verification

Retain valid ref-bearing receipts and fail closed on contradictory resource
combinations. Reuse real-repository retirement tests for branch-bearing and
detached targets, including actual stopped writers, same-HEAD siblings,
registration/HEAD drift, active/unknown consumers and interrupted removal.
Update the existing terminal plan with adjudication and delivery facts; do not
add another roadmap or preservation ledger. Only after exact proof, acceptance
and runtime readback may the historical detached source be physically retired.

Native Linux verification must supply the declared `lsof` observer and preserve
visibility across the test process environment. Installing the executable alone
does not repair a non-root test child that cannot inspect its root parent. The
existing CI bootstrap owns the prerequisite. For the Linux verification job it
also serves as the container entrypoint: provision first, preserve the Runner
script on stdin, prepare only the exact checkout and declared project cache,
then replace PID 1 with an unprivileged Runner shell. All proof and test children
inherit that identity. Ordinary bootstrap invocation never changes ownership;
entrypoint mode requires a root PID 1 and an exact native checkout.

Remove pytest-only identity controls, temporary identity homes, safe-directory
overlays and repeated ownership changes from the test gate. Keep native process
observation unchanged: unknown visibility still blocks, and filesystem and
process-limit negative tests must remain meaningful. No privileged runner,
visibility filter, custom image or alternate test engine is introduced.
