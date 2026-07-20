## Context

The target is an exact accepted ancestor, so Git graph inclusion proves that
its committed history is present in accepted history. The ordinary landed
retirement command correctly refuses a missing-owner source; authority must not
be inferred from missing lease state or from the source's historical evidence.

## Decision

Use one narrow current-base authority carrier. Its Claim, Chronicle, and
OpenSpec delta state why the exact source has been semantically absorbed and
delimit one later native `lane_resolution/retire` decision. The resolver—not
this document, a lane inventory, or a raw Git command—re-observes and effects
the irreversible operation.

## Risk Controls

- A changed source head, linked path, cleanliness, lease state, Chronicle, or
  accepted control state blocks the decision or its application.
- Break-glass and irreversible confirmation are mandatory for the one-source
  effect.
- No dirty source is covered; no historical runtime receipt is promoted to
  current proof.
- The carrier itself retires after the source transition, avoiding a permanent
  cleanup authority or a second retained worktree.
