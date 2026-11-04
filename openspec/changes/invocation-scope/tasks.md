# Tasks

## 1. One invocation per command

- [x] 1.1 Open one invocation scope per command, except the MCP server, in the entry point and the
      in-process test runner. Done when a test shows that a command observes an invocation fact once
      while `mcp` observes it each time, and the test failed before the change. The new test failed
      with `assert 2 == 1` before the scope existed. With it, the 18 tests of
      `test_invocation_facts.py`, Ruff and ty pass, and 2,566 tests of the CLI, lane, land and
      repository adapter suites pass, 3 skipped.
- [ ] 1.2 Measure the effect. Done when the native command count and command seconds of
      `tests/unit/cli/test_contracts_land.py`, run serially with the command-sites plugin, are
      recorded before and after, and the CLI, lane and land tests pass.
- [ ] 1.3 Name the change in the Unreleased notes. Done when the changelog validates.
