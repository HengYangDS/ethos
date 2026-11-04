# Design

## Context

See [proposal.md](proposal.md). `invocation_scope` reuses only successful reads of objects named by
their full object ID, the options whose output depends only on those objects, and declared
invocation facts such as the running build; refs, the index, the worktree and configuration stay
fresh, and failures are never reused. The scope is a context variable, and a nested scope joins
the outer one.

## Goals / Non-Goals

**Goals:**

- Each command observes an immutable object once, and the native command count of the measured
  module falls.

**Non-Goals:**

- Observing an OpenSpec projection once per tree, the analysis's second lever.
- Reusing facts across commands.

## Decisions

- **Open the scope at the entry point.** `main` wraps the dispatch in `invocation_scope`, so every
  command group gains it without a decorator of its own.
- **Not for the MCP server.** `ethos mcp` serves many requests in one process; its running build
  may change on disk between them, so it keeps observing.
- **The test runner matches the product.** `_run_inprocess` opens the scope per command, so tests
  observe what a real invocation does.

## Risks / Trade-offs

- [A command that changes its own checkout and then reads the running build sees the build it
  started with] → That is the build whose code is running; `invocation_facts.py` already defines
  the running build as one fact per invocation.
