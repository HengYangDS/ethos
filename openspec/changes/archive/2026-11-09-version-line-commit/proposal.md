# Proposal

## Why

Since `catalog-operations` moved the version projection, `ethos --version` prints an empty
source-commit field, `(…; ; OpenSpec …)`: the human line reads the identity from the result's frozen
data and accepts only a `dict`, while the JSON projection of the same result names the commit.

## What Changes

- The human version line reads the identity as any mapping and prints the first 12 characters of
  the source commit, as the JSON projection names it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: the human version line names the source commit of the same identity result.

## Impact

- `src/ethos/surface/cli/version.py` and `tests/unit/cli/test_version_command.py`.
