# Proposal

## Why

`supply-move-1112` moved Syft from 1.57.0 to 1.57.1. The release node declaration test pins the
locked Syft version, so that every Syft move rechecks whether Syft now classifies `node.exe`; when
it does, the release inventory's declaration path for Node is removed. Syft 1.57.1's release notes
list only dependency updates, so it still matches Node only in a file named `node`, and the pin
moves with the supply.

## What Changes

- The test's pinned Syft version and its docstring move to 1.57.1.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A test's pinned version moves; no behaviour changes, so `skip_specs: true` applies.

## Impact

`tests/unit/ci/delivery/test_release_node_declaration.py`.
