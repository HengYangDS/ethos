# Proposal

## Why

When a Work Lane holds two active Changes, every command that consumes intent needs to know which
one it serves. `plan` and `prove` accept `--change`, but `status`, `land` and `lane prewrite` read
only `ETHOS_CHANGE`, so an agent must set an environment variable around one command, and the MCP
`status` and `land` tools cannot select a Change at all. Where `plan` and `prove` accept the option,
it reaches their resolution and proof query, but not the readers that consult only the environment
or the child processes the command starts. The repository-governance requirement "Invocation-local
intent selection" already asks an explicit command or API Change to win over the environment input.
The 2026-11-07 expert committee's operation-catalog design names this as the first code Change of
the release candidate.

## What Changes

- `ethos status`, `ethos land` and `ethos lane prewrite` accept `--change <id>`, and the MCP `status`
  and `land` tools accept `change`, as `plan` and `prove` already do.
- An explicit Change binds the whole invocation: every reader in the call and every child process
  it starts, such as the Git hooks of a landing, sees the same Change, and the inherited
  `ETHOS_CHANGE` returns when the call ends. `plan` and `prove` use the same binding.
- The two remedies that told an agent to unset `ETHOS_CHANGE` name both selection inputs.
- The command reference documents the option.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: the intent-consuming commands accept an explicit Change that binds the whole
  invocation.

## Impact

- `src/ethos/adapters/openspec/selection.py`, the status, plan and land operations, the `prove` and
  `lane prewrite` commands, and two remedies under `src/ethos/adapters/openspec/`.
- `docs/reference/command-plane.md` and tests.
- `ETHOS_CHANGE` stays the fallback; the catalog design retires it later, after one window.
