## Context

The retirement model deliberately separates semantic absorption from raw tree
equality.  The historical source contains dated evidence and archive bytes that
must not be copied merely to satisfy a structural comparison.  The current
implementation is accepted through a current-base replay and the standard local
proof-to-closeout lifecycle.

## Decision

Use the existing two-phase exceptional resolver with the `retire` disposition.
The source is clean, so the resolver may retire without a preservation package,
but only after it recomputes the exact observation and records a receipt.  The
accepted Chronicle token is scoped to the named source and cannot become a
general missing-lease deletion rule.

## Risk controls

- Drift in source head, worktree binding, cleanliness, or lease facts invalidates
  the native decision before effect.
- Any semantic uncertainty keeps the lane blocked rather than substituting a
  package, tree comparison, or raw Git deletion.
- Remote and hosted authority planes remain independent of local closeout.
