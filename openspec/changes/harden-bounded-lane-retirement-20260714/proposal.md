## Why

A targeted `ethos lane retire landed --branch <owned-lane>` currently evaluates
every registered Work Lane before narrowing to the requested branch. A stale
foreign worktree path can therefore raise `FileNotFoundError` and prevent the
owner from retiring its otherwise proven, merged lane. The failure is a local
control-plane robustness defect: it neither produces a bounded verdict nor
preserves the requested lane's lifecycle path.

## What Changes

- Restrict branch-targeted landed-retirement inspection to the selected Work
  Lane before any lane-local Git status call.
- Make lane cleanliness inspection fail closed for unavailable paths, returning
  a deterministic blocked retirement state rather than raising an exception.
- Add regression coverage proving a missing foreign worktree cannot block a
  matching owner's targeted retirement, while unavailable selected lanes remain
  non-retireable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: bounded landed-lane retirement must not inspect or
  mutate unrelated foreign Work Lanes, and unavailable target paths must remain
  fail-closed.

## Impact

Affected surfaces are ETHOS lane-retirement adapters, their unit coverage, and
one OpenSpec archive. No remote probe, remote publication, adopter runtime, or
foreign lane cleanup is performed.
