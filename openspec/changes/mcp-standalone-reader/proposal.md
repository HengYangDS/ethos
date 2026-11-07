# Proposal

## Why

`bounded-reader-guard` routed the MCP acceptance's CLI calls through
`tools.ci.delivery.acceptance.invocation.invoke`. The installed-package smoke, however, runs
`tools/ci/delivery/acceptance/mcp.py` as a standalone script under `python -I` in the installed
package's environment, where the repository's `tools` package does not exist. The hardening lane's
proof hdp1 (2026-11-07 12:41) therefore failed `local-install-smoke` with
`ModuleNotFoundError: No module named 'tools'`, and `release-sbom` failed with it, as its
dependency.

## What Changes

- The MCP acceptance reads a CLI result with the installed package's own
  `ethos.result.expand_result`, so it still reads a bounded result in full and it imports only the
  installed package and its declared clients.
- An architecture test pins that the script imports no `tools` module.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The acceptance script is qualification tooling, so `skip_specs: true` applies.

## Impact

`tools/ci/delivery/acceptance/mcp.py` and `tests/architecture/test_bounded_result_readers.py`.
