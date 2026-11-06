# Design

## Context

See [proposal.md](proposal.md). `dependency-hygiene` requires each direct dependency's declared
floor to equal its locked version. `module-layout` refuses `from package import submodule` and a
private name imported across modules.

## Goals / Non-Goals

Goals:

- The lane's readiness tier passes.

Non-goals:

- Changing either rule.

## Decisions

- **Raise the floors to the lock.** This is the rule the gate states. A lock move moves the
  declared floor with it.
- **A local helper.** The test declares its two-node graph itself, instead of importing a private
  helper from another test.

## Risks / Trade-offs

- None beyond the gates themselves, which re-run on the fixed head.
