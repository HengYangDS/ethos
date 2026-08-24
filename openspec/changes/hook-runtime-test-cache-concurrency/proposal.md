## Why

The test suite repeatedly built and cloned the same immutable hook runtime in
each pytest-xdist worker. A process-wide lock also covered each repository
clone, so otherwise independent tests exhausted the per-test timeout while
waiting on test infrastructure rather than exercising product behavior.

## What Changes

- Share one content-addressed runtime-template cache across all workers in one
  pytest run.
- Build the template once in the pytest controller before xdist workers start;
  retain locked recovery for a missing template, but move each repository-local
  clone outside the publication lock.
- Validate every cached runtime template before reuse and retain
  inode-independent runtime trees under each fixture repository's Git common
  directory, using native copy-on-write where the platform provides it.
- Add focused tests for worker-root convergence, controller publication,
  repository isolation, path-valid relocation, and invalid-template rejection.
- Do not change production runtime installation, package identity, governance
  semantics, or any adopter policy.

## Capabilities

### New Capabilities

None. This is test-infrastructure optimization only.

### Modified Capabilities

None. Product behavior and public contracts are unchanged.

## Impact

Only the pytest fixture bootstrap and its test support module change. The
result reduces duplicate package/runtime construction and lock contention in
parallel unit and architecture tests without weakening production acceptance.
