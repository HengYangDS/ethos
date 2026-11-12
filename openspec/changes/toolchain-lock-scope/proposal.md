# Proposal

## Why

The repository paradigm requires a tracked `.config/mise/mise.lock` whenever
`.config/mise/config.toml` is tracked. `mise lock` writes no lock for a configuration that selects
no tool: mise 2026.11.7 answered "No tools configured to lock in this project" on 2026-11-12. A
repository whose mise configuration only declares tasks, such as the `foundation` starter that
`ethos adopt --create` will write, can then conform only with a placeholder lock that no native
tool wrote. ETHOS's gates already treat such a configuration as task-only and need no lock.

## What Changes

- One predicate, whether a mise declaration selects tools, owns the rule for both the paradigm and
  the gates: a `[tools]` table with entries, idiomatic version files turned on, or `.tool-versions`.
- The paradigm requires the lock only when the configuration selects a tool. `locked = true` and the
  three verbs stay required.
- The Unreleased section of `CHANGELOG.md` gains a Changed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: `One locked toolchain owner exposes the common verbs` gains the task-only
  case.

## Impact

`src/ethos/repository/paradigm/toolchain.py`, `src/ethos/adapters/toolchain/mise.py`,
`tests/unit/repository/test_paradigm_toolchain.py` and `CHANGELOG.md`.
