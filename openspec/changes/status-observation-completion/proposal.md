## Why

The accepted repository reader points to lane status when no local transition
is pending. Lane status repeats that same observation as its next action, so a
completed read never terminates. The root cause is an unconditional fallback,
not missing workflow state. Entry documentation also contradicts the transient
Commitment contract and the actual two-file adoption plan.

## What Changes

- Let complete coordination observation end without inventing another task.
- Keep one bounded detail expansion for compact status when advisories exist.
- Reuse the current closeout decision when a candidate actually needs acceptance.
- Align README, quickstart and agent guidance with the same authority and
  continuation semantics; retain research obligations in the existing plan.

## Capabilities

### Modified Capabilities

- `command-plane`: a reader continues only to an unobserved boundary or a
  currently selected operation; complete observation can terminate.

## Impact

Workspace stage projection, status and lane-status transports, their existing
tests, README, quickstart, repository skill and the existing terminal plan.
No new lifecycle store, generic loop detector, tool registry or authority is
introduced. Native docstring enforcement, OpenSpec supply upgrade, independent
verification and complete adoption workloads remain separate owner-level work.
