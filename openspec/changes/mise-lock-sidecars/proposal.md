# Proposal

## Why

Since 20:13 on 2026-11-06 the host has run mise 2026.11.2, and ETHOS beta.4 now reports npm tools
that have aube lock sidecars as missing. wib's `controlled-web-ingestion-behavior` gate blocks with
`quality_behavior_mise_supply_incomplete:npm:prettier@3.9.10`. aigw-cli and architecture-publisher
reproduce the same way (fbee0c, 20:2x).

ETHOS resolves the supply in a disposable copy that holds only the mise config and the lock. mise
2026.11.2 keeps the aube graph in safe mode (jdx/mise#15401) and derives an npm tool's install path
from `.config/mise/locks/<tool>/<version>/aube-lock.yaml`. Without that sidecar in the copy, the
tool resolves as not installed.

## What Changes

- The supply closure that `repository_mise_files` selects includes every file of each aube sidecar
  directory the lock names. `run_mise` writes those files into the copy and re-checks each one
  against the repository, as it already does for declared version carriers.
- The mise boundary test follows native trust policy under 2026.11.2, which resolves a locked aube
  install for an untrusted copy in safe mode. That expectation failed ETHOS's own full proof under
  the new host mise.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies: the supply already has to resolve exactly the declared and
locked tools.

## Impact

- `src/ethos/adapters/toolchain/mise.py` and `tests/unit/adapters/toolchain/`.
- Acceptance outside ETHOS: the `*-behavior` gates of wib, aigw-cli and architecture-publisher pass
  under host mise 2026.11.2 with the fixed runtime, as the Homebrew owner requires before any pin
  change.
