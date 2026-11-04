# Proposal

## Why

A CLI command observes the same immutable Git objects and the running build again and again,
because `ethos/cli.py:main` opens no invocation scope; only `plan`, `status`, `adopt`, `land` and
`publish` open one through `application_result`. On 11-04 the 26 tests of
`tests/unit/cli/test_contracts_land.py` started 9,723 native commands, 145 of their 170 seconds,
and only 1,985 of them ran inside a scope. The test gate is the critical path of every proof
(1,311 of 1,362 seconds locally and 30.9 of 33.5 minutes on GitHub) and process creation is
slowest on Windows, so these repeated reads cost every landing. The lever was measured on 10-24
(`build/evidence/proof-critical-path/9.2.5-subprocess-volume/analysis.md`) and never delivered; the
committee review of the iteration-speed design ranks it first.

## What Changes

- Every ETHOS command runs inside one invocation scope, so an immutable object read and the running
  build are observed once per command, as `invocation_facts.py` already defines. The long-running
  MCP server keeps no invocation facts, since it serves many requests in one process.
- The in-process test runner opens the same scope for each command it runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The quality specification already requires a later invocation to observe a changed ref
rather than a cached verdict; only the scope's coverage widens, so `skip_specs: true` applies.

## Impact

`src/ethos/cli.py`, `tests/support/ethos_cli_runner.py`,
`tests/unit/adapters/repo/test_invocation_facts.py` and `CHANGELOG.md`.
