# Proposal

## Why

`peer-identity-redaction` and `peer-identity-push-check` were archived in their lane before
`prewrite-index-target` landed at `142092d35`. Refreshing the lane onto that accepted candidate
conflicts only where both sides added entries: the CHANGELOG's Unreleased Added list and the
repository-governance specification's requirement list. An archived Change admits no paths, so
this Change owns the merge resolution.

## What Changes

- The lane merges the accepted candidate `142092d35` through
  `ethos lane refresh-base --strategy merge`, and its resolution keeps every entry of both sides:
  the CHANGELOG lists the index-target entry first, then the two peer identity entries, and the
  specification lists the index-target requirement before the four peer identity requirements.
- No product code, test, specification meaning or behavior changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- `CHANGELOG.md` and `openspec/specs/repository-governance/spec.md`, through the merge commit only.
