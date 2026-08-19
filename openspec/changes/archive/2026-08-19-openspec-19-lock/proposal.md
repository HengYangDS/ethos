## Why

The repository currently locks `@fission-ai/openspec` to 1.8.0 while the
stable registry release is 1.9.0. The project must use one declared package
identity so local, CI, and package-only lifecycle execution do not drift.

## What Changes

- **BREAKING**: lock the repository package and lockfile to `@fission-ai/openspec@1.9.0`.
- Update current (non-archived) contract, runtime documentation, and tests to
  name the locked 1.9.0 package.
- Validate the Change with the official OpenSpec 1.9 CLI and npm lockfile.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a dependency and current-contract synchronization change; it
does not change ETHOS product behavior.

## Impact

The package declaration, npm lockfile, current governance specification,
current runner documentation, and the archive-transition contract test change.
Historical OpenSpec archive records remain unchanged.
