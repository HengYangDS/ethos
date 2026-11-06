# Design

## Context

See [proposal.md](proposal.md). `emit` adds `summary.runtime` to every CLI JSON result. The MCP
server registers each domain operation with `FunctionTool.from_function(partial(operation, root))`
and returns its result as structured content without `emit`.

## Goals / Non-Goals

Goals:

- Every surface's result names the build that produced it, so the surfaces stay equal.

Non-goals:

- Bounding MCP results, which the `mcp-forms` slice owns.

## Decisions

- **One shared module.** `with_runtime` lives in `ethos/surface/runtime_identity.py`, which imports
  only the result model and the build identity owner, so `ethos --version` still loads no Cyclopts
  and the MCP server imports nothing from the CLI.
- **Wrap, keep the signature.** The server wraps each operation with `functools.wraps`, so the
  tool's input schema, derived from the signature, does not change.

## Risks / Trade-offs

- An MCP result larger than the CLI budget still differs from the CLI's bounded result. The
  install smoke compares a small `adopt` preview; `mcp-forms` makes MCP results bounded too.
