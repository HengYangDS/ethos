# Tasks

## 1. Standalone MCP acceptance

- [x] 1.1 Specify with an architecture test that the MCP acceptance imports no `tools` module. Done
      when it fails on the current script. Red at 13:20:48: the script imported
      `tools.ci.delivery.acceptance.invocation`, as proof hdp1's install smoke had failed.
- [x] 1.2 Read the CLI result through the installed `ethos.result.expand_result`. Done when that
      test, the reader guard and the MCP acceptance tests pass, and the script starts under
      `python -I` without the repository's `tools`. Green at 13:22:15: 13 guard and MCP acceptance
      tests pass, the script starts under `python -B -I` from the lane's environment, and Ty and
      ruff pass.
