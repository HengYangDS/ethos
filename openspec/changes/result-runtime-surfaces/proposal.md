# Proposal

## Why

The full proof of the archived `result-contract` head refused `local-install-smoke`. The smoke
checks that the CLI and the MCP server return exactly the domain operation's result for `adopt`.
After `result-contract`, the CLI adds `summary.runtime` in `emit`, but the MCP server never passes
through `emit`, so the two surfaces disagree. The product design contract requires CLI, SDK and
MCP to expose the same context, and the command-plane scenario says every JSON result names its
runtime.

## What Changes

- `with_runtime` moves from `ethos/surface/cli/runtime_identity.py` to
  `ethos/surface/runtime_identity.py`, shared by every surface.
- The MCP server wraps each tool's operation so its result names the build that produced it.
- The install smoke's expected result and the MCP binding tests apply `with_runtime` to the domain
  result, as the CLI tests already do.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies: the command-plane scenario already requires every JSON result
to name its runtime.

## Impact

- `src/ethos/surface/runtime_identity.py`, `src/ethos/surface/cli/output.py`,
  `src/ethos/surface/cli/version.py` and `src/ethos/surface/mcp/server.py`.
- `tools/ci/delivery/acceptance/mcp.py` and the tests that import `with_runtime`.
