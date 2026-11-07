# Design

## Context

See [proposal.md](proposal.md). The MCP acceptance serves two consumers: source tests import it, and
the installed-package smoke runs it as a script inside the package's environment.

## Goals / Non-Goals

Goals:

- The script runs standalone in the installed package's environment again.
- It still reads a bounded CLI result in full before it compares surfaces.

Non-goals:

- Any change to the shared reader `invocation.invoke` or to the guard's triggers.

## Decisions

- **Expand with the installed package.** The CLI's stdout is parsed and passed to
  `ethos.result.expand_result`, which every consumer of the package already has. This keeps the
  guard's rule, a parse of an ETHOS result goes through `expand_result`, without the repository's
  `tools`.
- **Pin the boundary.** The guard's module gains a test that parses the script's imports and
  refuses any `tools` import, because only the installed smoke would otherwise notice.

## Risks / Trade-offs

- The script keeps its own small subprocess call beside `invocation.invoke`. That duplication is
  the price of running without the repository.
