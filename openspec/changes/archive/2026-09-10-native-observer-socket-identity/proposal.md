## Why

Linux process observation rejects a valid Unix socket record emitted while
`uv` supervises repository commands. A socket inode without a filesystem device
is not an incomplete regular-file identity. This prevents otherwise valid
reviewed retirement and makes hosted verification fail.

## What Changes

- Interpret native process records according to their resource type in the
  existing process adapter.
- Retain complete device/inode identities for filesystem references and reject
  incomplete, malformed or inaccessible observations.
- Verify the actual `uv`, Nox and pytest execution chain rather than relying on
  direct-interpreter tests alone.

## Capabilities

### Modified Capabilities

- `adapters`: native process observation distinguishes socket identifiers from
  filesystem identities without weakening retirement admission.

## Impact

The existing process adapter, its regression matrix and the canonical execution
plan. No new observer, subprocess policy, privilege mechanism, dependency,
state carrier or adopter modification.
