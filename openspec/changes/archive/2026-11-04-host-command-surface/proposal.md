# Proposal

## Why

The beta.2 full proof at `83b269669` failed one test:
`tests/unit/cli/test_terminal_command_surface.py::test_registered_command_roots_are_exactly_the_terminal_surface`.
The test pins the exact set of registered roots, so that a new root is added on purpose. The
`host-admission` Change registered `host` for `ethos host run` but did not update that set.

The command-plane specification keeps maintainer mechanics "hidden or semantically namespaced".
`host` is a semantic namespace for host-level admission. Like `attestation`, it is listed in the
root help so that renders, model runs and other test runners can find the command that admits
them.

## What Changes

- The terminal surface test names `host` beside `lane`, `hook` and `attestation`, as the roots
  registered beside the workflow commands and the MCP launcher.
- No product code changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The command-plane requirement already allows a semantically namespaced root, so
`skip_specs: true` applies.

## Impact

`tests/unit/cli/test_terminal_command_surface.py`.
