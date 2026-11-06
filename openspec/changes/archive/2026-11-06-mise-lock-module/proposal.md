# Proposal

## Why

The readiness run on the archived `mise-lock-sidecars` head refused `repository-audit` with
`repository_paradigm_code_size:src/ethos/adapters/toolchain/mise.py`. The module grew from 481 to
513 effective lines, past the 500-line ceiling, when it gained the sidecar reader.

## What Changes

- The lock readers move to `src/ethos/adapters/toolchain/mise_lock.py`: the aube sidecar
  directories a lock declares, and whether a lock entry references a dependency graph. `mise.py`
  keeps the native boundary and imports them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `src/ethos/adapters/toolchain/mise.py` and the new `src/ethos/adapters/toolchain/mise_lock.py`.
