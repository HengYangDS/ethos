## Why

Linked-lane retirement can currently remove a worktree before a later Git
process fails, leaving an unbound ref and Lease that the original request cannot
resume or compensate. A destructive transition must preflight every execution
coordinate and persist enough exact progress to converge safely after any
partial effect.

## What Changes

- Replace linked-lane retirement's implicit sequential cleanup with one
  declarative, receipt-backed effect state machine.
- Preflight the resolved Git executable and every effect working directory
  before the first destructive effect.
- Persist immutable request coordinates plus observed `completed_effects` and
  `remaining_effects` after each step.
- Add one public `ethos lane retire recover` command that re-observes the exact
  request and resumes only the safe remaining effects toward the declared
  terminal state.
- Make repeated recovery idempotent and keep active foreign ownership,
  ambiguous drift, and mismatched receipt bytes fail closed.
- Return `partial_transition` with the exact recovery command whenever an
  effect completed but terminal postconditions did not.
- Do not add legacy receipt compatibility, raw Git guidance, or an independent
  recovery authority.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Linked-lane retirement becomes a resumable,
  exact-observation transition whose receipt is the sole continuation input.
- `command-plane`: The public lane retirement family exposes one structured,
  copyable recovery route for partial destructive effects.

## Impact

- Affected semantic owner:
  `src/ethos/adapters/mutation/lane_retirement/`.
- Affected public projection:
  `src/ethos/surface/cli/lane/retirement.py`.
- Affected contracts and tests: repository-governance and command-plane
  OpenSpec deltas, receipt schema/projection tests, linked retirement failure
  branches, CLI recovery tests, and one package-only real-Git regression.
- No AIGW or Proxy files, refs, worktrees, Leases, or state databases are
  modified by this Change.
