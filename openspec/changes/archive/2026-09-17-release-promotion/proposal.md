## Why

Independent release has no public accepted-to-main transition. Local ref hooks
leave that role unclassified, and tag publication assumes every product owns
VERSION. Publication also treats accepted source as another integration and
rechecks pre-adoption history under later policy.

## What Changes

- Promote exact accepted source through existing land and Git effect owners,
  optionally creating a native signed annotated tag in the same ref transaction.
- Reuse verified acceptance only for exact accepted delivery; keep ordinary
  introduced-range checks for new contributions and unverified publication.
- Read the product's native committed version owner instead of requiring a
  parallel VERSION carrier.
- Verify linked worktrees, stale CAS, trust, recovery and independent peers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: proof-bound independent release delivery.

## Impact

Existing land, ref admission, native Git object, commit-range, release identity
and publication owners, their tests, and the canonical terminal plan.
No adopter edits, history rewrite, extra lifecycle, duplicate version carrier,
deployment or Forge Release/assets creation. Cold-CI history-repair material
transport remains a separate closure.
