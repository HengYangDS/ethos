## Context

The target is an exact accepted ancestor, so Git graph inclusion proves that
its committed semantic content is present in accepted history.  The ordinary
landed command nevertheless requires a currently authoritative holder context;
the source has no active lease and must be treated as owner-uncertain.

## Decision

Use one narrow current-base authority carrier.  Its Claim, Chronicle, and
OpenSpec delta explain why this exact landed source is absorbed and delimit a
later native `lane_resolution/retire` decision.  The resolver—not this document
or an inventory—will re-observe the source and execute the irreversible effect.

## Risk Controls

- A changed source head, linked path, cleanliness, lease state, Chronicle, or
  accepted control state blocks the decision or its application.
- Break-glass and irreversible confirmation are mandatory for the one-source
  effect.
- No dirty source is covered; none may be treated as clean merely because its
  committed head is accepted.
- The carrier retires after the source transition so it does not become a
  permanent worktree or standing cleanup authority.
