## Context

The exact source ref is ownerless and diverged because its historical carrier
contains proof and archive bytes in addition to the useful bootstrap behavior.
Accepted source has independently evolved that behavior on the current
baseline. A preservation package or a tree comparison cannot establish this
semantic fact.

## Goals / Non-Goals

**Goals:**

- Bind one exact source ref to the accepted semantic basis and to a later
  native local resolution decision.
- Preserve the separation between absorption, local closeout, retirement,
  remote publication, and hosted CI.

**Non-Goals:**

- Change product behavior, merge/rebase the historical lane, take a lease,
  delete any other ref, or publish to a remote.

## Decisions

- Use the existing two-phase `lane_resolution/retire` path after a fresh clean
  linked-worktree observation. It records the mutable observation before an
  irreversible effect and emits the receipt after it.
- Treat the accepted implementation, canonical contract, and focused tests as
  the absorption basis. Do not replay historical archive/evidence bytes merely
  to make a tree comparison succeed.

## Risks / Trade-offs

- [Target or control-state drift] -> native decision/apply recomputes the
  observation and blocks on any mismatch.
- [Semantic overreach] -> the Claim and Chronicle name one ref and one SHA;
  no inventory entry becomes batch authority.
