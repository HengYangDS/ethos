## Why

The archived terminal source Change correctly migrated its unfinished outcomes,
but current accepted specifications still mix implemented behavior with stale
historical requirements. The first declared successor also cannot start through
the public command plane because lane creation requires a live source lane that
the source Change was required to retire.

## What Changes

- Reconcile accepted specs against current source, tests, schemas, and verified
  behavior; remove requirements that only describe retired implementations.
- **BREAKING** Make a new atomic Change start from clean accepted truth with one
  explicit Commitment input; a retired source lane is not required.
- Preserve source-lane derivation only for an actually live, owned Change
  continuation; never resurrect an archived carrier or infer intent from history.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: make fresh Change/Work Lane bootstrap atomic and source-lane
  continuation explicit.
- `repository-governance`: keep accepted specs authoritative only for behavior
  proved by current implementation and define the successor bootstrap boundary.

## Impact

The lane-start command, OpenSpec adapter boundary, Lease binding, accepted
specifications, focused lifecycle tests, and command documentation change. No
legacy lane is revived and no second task or lifecycle store is introduced.
