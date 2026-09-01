## Why

`ethos plan --changed` currently rehydrates the latest archived Change even when
fresh Git observation reports no changed paths. The resulting historical archive
scope is then compared with an empty current scope, so clean repositories are
incorrectly blocked by `proof_archive_scope_stale`.

## What Changes

- Treat an empty fresh changed-path set as a closed, no-op planning result.
- Do not select active or archived OpenSpec intent when `--changed` has no input
  paths.
- Preserve strict archive-scope validation whenever changed paths do exist.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: define the observable result of changed-scope planning for a
  clean repository.

## Impact

The public `plan --changed` result, its current-resolution orchestration, and
focused command/kernel regression tests change. Archive transition admission and
historical proof validation remain unchanged.
