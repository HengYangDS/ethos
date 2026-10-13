## Why

A Work Lane retirement receipt pins the exact accepted head. On 2026-10-13 another lane's ordinary land advanced `dev` from 2498e9fff to 54bd85aa0 while receipt ddb7fe1a was being applied.

Deletion correctly stopped before the branch ref was touched, but the report was wrong in three ways:

- It returned `retirement_operation_state_drift` with no progress, although the worktree had already been removed.
- It left the persisted progress at `ready`.
- It advertised `ethos lane retire recover` for the same immutable receipt. That command can never succeed, because the accepted coordinate cannot return.

A reviewed-content drift before any deletion led to the same dead end. The only way out was a manual unbound `superseded --path` retirement.

## What Changes

- The accepted head is an admission coordinate, not a retirement carrier, and it gets its own `AcceptedState`. A fast-forward of the accepted ref is observed as `advanced`. Progress is then reduced from the worktree, ref and Lease carriers alone, and it is persisted and reported. Any other accepted move, such as a rewrite, a rewind or an absent ref, remains `retirement_operation_state_drift`.
- An `advanced` accepted coordinate fails closed with `retirement_accepted_coordinate_drift` before any remaining worktree or ref deletion. Revoking the exact Lease after both carriers are gone still completes.
- When a failure invalidates the immutable receipt, through accepted coordinate drift or reviewed content drift, the continuation becomes the native fresh admission for the remaining carriers, derived from current facts instead of `recover`. When carrier state drifts, the continuation is `ethos lane status`.
- A dry-run that meets a failure no longer persists a progress receipt.

## Impact

- Code:
  - `src/ethos/adapters/mutation/lane_retirement/operation.py`;
  - a new continuation owner, `continuation.py`;
  - import updates in `linked.py` and `abandonment.py`.
- Specs: command-plane `Lane retirement exposes one receipt-bound recovery route`.
- Unchanged:
  - the receipt schema;
  - mode admission;
  - the exact accepted assertion of the ref-deletion effect;
  - the rule that a stale receipt never substitutes for a missing fact.
