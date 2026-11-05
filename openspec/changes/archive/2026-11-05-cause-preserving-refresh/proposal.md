# Proposal

## Why

This lane's two Changes, `cause-preserving-results` and `integrity-mismatch-verdict`, are archived.
Refreshing the lane onto the candidate, which now carries 0.2.0-beta.2 and `repository-exit`,
produced conflicts in two files where both sides only added text:

- `CHANGELOG.md`: this lane's Unreleased notes against the new 0.2.0-beta.2 entry;
- `openspec/specs/quality/spec.md`: this lane's integrity requirement against beta.2's host
  admission requirements, at the same position.

## What Changes

- The merge keeps both sides. The lane's notes stay under `## [Unreleased]` above the released
  entries, and both requirements stay, the candidate's first.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The resolution keeps both sides unchanged, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md` and `openspec/specs/quality/spec.md`, in the merge commit only.
