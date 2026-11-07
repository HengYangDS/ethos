# Tasks

## 1. Guard and readers

- [x] 1.1 Add the architecture test with its planted cases. Done when it reports exactly the two
      readers that miss the bound today, `mcp.py` and `gates/verification.py`. At 12:10:03 the
      whole-tree check failed on 3 readers, and its 10 planted cases passed. Two readers miss the
      bound today: `gates/verification.py:88` and `tools/ci/delivery/acceptance/mcp.py:137`. The
      third, `openspec/configuration.py:66`, reads its own Node helper's report, which no bound
      shortens, so it is declared by name.
- [x] 1.2 Read the MCP acceptance through `invocation.invoke` and expand in gate verification. Done
      when the architecture test, the gate verification tests and the MCP acceptance test pass.
      Green at 12:17:12: 604 guard, gate, MCP, delivery and result-bound tests pass. At 12:18:06 the
      284 architecture tests pass. Ty and ruff pass.
