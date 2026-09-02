## Why

The current repository resolver already owns the selected official OpenSpec
intent for status, plan, prewrite, hooks, and the public proof path, but archive
still reads lifecycle state again and its effect compiler reloads Commitment
from the repository. One archive invocation can therefore validate one
projection and bind a different one into its `TransitionPlan`.

## What Changes

- Extend the existing current-resolution owner to the OpenSpec archive
  operation without creating another resolver or persistent carrier.
- Resolve authority and active intent once before archive mutation; make
  readiness and effect-plan compilation consume that exact result.
- Reconstruct an interrupted staged archive from the exact source HEAD through
  the same resolver, while preserving effect-time CAS checks and post-effect
  observation.
- Delete archive-local OpenSpec governance and Commitment-selection fallbacks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Extend the current repository resolution boundary through
  OpenSpec archive planning and recovery.

## Impact

The change affects current resolution, archive command orchestration, archive
effect compilation, and focused lifecycle tests. It does not modify adopters,
add persistent state, redesign the archive effect, or absorb proof and accepted
closeout convergence that can be completed as independently useful successor
Changes.
