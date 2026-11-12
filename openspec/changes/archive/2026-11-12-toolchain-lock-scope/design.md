# Design

## Context

See the [proposal](proposal.md). `toolchain_gaps` in `src/ethos/repository/paradigm/toolchain.py`
reports `toolchain-lock` for an untracked lock whenever the mise configuration is tracked.
`_task_only_configuration` in `src/ethos/adapters/toolchain/mise.py` decides, for the gates, that a
readable declaration with no tools and no idiomatic version files is task-only, and
`repository_mise_files` then selects no mise toolchain unless `.tool-versions` exists. The adapter
layer may import the repository layer; the reverse is refused.

## Goals / Non-Goals

Goals:

- The paradigm and the gates agree on when a mise configuration needs a lock, through one function.
- A task-only configuration conforms without a placeholder lock.

Non-Goals:

- Any change to `locked = true`, the three verbs or the npm owner.
- Writing a lock for anyone: a configuration that selects a tool keeps needing `mise lock`.

## Decisions

1. `selects_tools(declared, *, tool_versions)` lives in `repository/paradigm/toolchain.py`. It is
   true when `tools` has entries, when `settings` is not a table or turns on
   `idiomatic_version_file_enable_tools`, or when `.tool-versions` exists, which is the gates'
   current rule.
2. The paradigm reports the lock only when `selects_tools` is true, with `.tool-versions` read from
   the tracked paths.
3. The gates' `repository_mise_files` uses the same function; an unreadable declaration still needs
   its lock, as today.
4. Tests: the `unlocked` case gains a tool so it still reports both lock gaps, and a new case shows
   that a task-only configuration conforms without a lock. The adapter's task-only tests keep
   passing unchanged.

## Risks / Trade-offs

- A repository that later adds a tool must add the lock in the same change; the paradigm then
  reports it, as for any other repository.
