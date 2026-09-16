## Why

An owned lane starting at an accepted archive commit inherits an earlier merge's
contribution selection. A different active Change is then shadowed by archived
intent, blocking valid authoring and producing inconsistent proof observations.

## What Changes

- Bound contribution provenance by the lane's existing native creation effect;
  historical merges before that boundary do not own its current active intent.
- Preserve same-lane archive attribution, explicit Change selection, ambiguous
  intent rejection and independent current Lease/proof bindings.
- Verify public prewrite, plan and proof across archive, acceptance and a new lane
  on the same source object, without adding tracked or Lease intent carriers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: select current lane intent without allowing an
  archived predecessor to displace a different active Change.

## Impact

Existing OpenSpec selection/current-resolution and proof consumers with native
regressions. No adopter mutation, persisted intent index, new Lease fields,
second lifecycle or remote publication policy change.
