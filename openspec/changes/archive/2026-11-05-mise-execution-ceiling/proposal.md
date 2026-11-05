# Proposal

## Why

A gate child that runs `mise` from the repository reads the operator's own mise configuration. The
environment that `locked_environment` hands to gate children sets `MISE_CEILING_PATHS` to the
parent of a temporary directory, which is not an ancestor of the repository. So mise's walk from
the repository goes up to the home directory. There it loads `~/.config/mise/config.toml` and
`~/.config/mise/conf.d/*.toml` as an ancestor's configuration: mise warns that a
`github.credential_command` "in non-global config" is ignored.

e7fae35e found this when archpub's npm test took the operator's npm 12.2.2, and 1 of 220 tests
failed. fbee0c reproduced it with mise 2026.10.25 on DDWG and wib: under the current ceiling each
repository's current tools gain npm 12.2.2. With the repository's parent as the ceiling, only the
repository's own configuration loads. Resolution already stops at the repository's parent, so
execution exposed a toolset that resolution never admitted. The requirement on locked execution
already demands configuration isolation.

## What Changes

- The execution environment's ceiling also holds the repository root's parent, so a gate child's
  mise reads the configuration that resolution resolved, and nothing above the repository.
- The operator's global configuration stays as it is: it is the operator's choice, and ETHOS
  isolates from it rather than reverting it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a scenario states that locked execution reads no configuration above the repository.

## Impact

`locked_environment` in `src/ethos/adapters/toolchain/mise.py` and a native mise regression in
`tests/unit/adapters/toolchain/test_mise_boundary.py`. Adopter gates that call `mise exec` or
`mise x` stop seeing the operator's global tools, environment and tasks.
