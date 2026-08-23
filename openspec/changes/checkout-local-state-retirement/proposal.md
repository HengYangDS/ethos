# Change: Retire checkout-local mutable state

## Why

The implementation still accepted and migrated mutable ETHOS state under a
checkout even though the canonical kernel contract assigns all coordination
state to the Git common directory. That compatibility plane created a second
state owner, extra public command surface, and divergent behavior across linked
worktrees.

## What Changes

- **BREAKING**: remove checkout-local `.ethos/state/**` as a readable or writable
  runtime location.
- **BREAKING**: remove the `ethos migrate-local-state` command and its migration
  implementation rather than retaining an alias, fallback, or compatibility
  reader.
- Route Lease, lifecycle, hook-admission, and digest-bound proof artifact access
  through the sole Git-common state owner.
- Remove checkout-local state declarations, ignore rules, generated-artifact
  allowances, documentation, fixtures, and migration-only tests.
- Preserve fail-closed public proof behavior when no Git repository/common
  directory exists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is destructive conformance to the existing `kernel` and
`command-plane` contracts, which already require Git-common mutable state and
exactly six public commands.

## Impact

Affected surfaces are the state-store adapter, Lease and lifecycle consumers,
proof artifact storage, CLI registration, repository policy, documentation,
fixtures, and tests. Existing checkout-local residue is not silently imported;
its disposition requires separate evidence-bound operator handling rather than a
permanent second reader.

## Out Of Scope

- No new recovery service, migration ledger, compatibility facade, or state
  schema.
- No deletion of unproven historical residue in other worktrees.
- No change to tracked `.ethos/` repository declarations or Git authority.
- No implementation of adopter break-glass, lane-start repair, runtime arming,
  or archive-closeout behavior in this atom.
