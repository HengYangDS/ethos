# Design

## Context

See [proposal.md](proposal.md). `module-layout` refuses `from package import submodule`.
`source-budget` holds the Python tests to a terminal ceiling of 95,000 effective lines, and the
ceiling policy removes accidental complexity before any raise.

## Goals / Non-Goals

Goals:

- The lane's readiness tier passes, without raising the ceiling.

Non-goals:

- Changing either rule or any production code.

## Decisions

- **Import by full path.** The runtime test imports `ethos.surface.cli.runtime_identity` itself.
- **Remove plumbing the new default made redundant.** `run_ethos` returns the full result by
  default, so `full_payload=True` arguments add nothing. Where an argument was the only reason a
  call wrapped, removing it shortens the call. `expand_payload` only delegated to `expand_result`.
- **One parametrized test** checks that a command's own `data.artifact_reference` and
  `data.detail` survive beside `bound`.

## Risks / Trade-offs

- None beyond the gates, which re-run on the fixed head.
