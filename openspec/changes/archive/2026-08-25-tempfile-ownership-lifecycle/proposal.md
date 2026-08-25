## Why

ETHOS-created test/build trees leak.

## What Changes

- Reclaim owned pytest basetemp but preserve caller paths.
- Retain supply through build consumption, then reclaim it.

- `repository-governance`: owned basetemp cleanup.
- `distribution`: build-scoped supply.
