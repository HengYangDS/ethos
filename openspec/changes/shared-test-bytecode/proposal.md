## Why

The Python test gate sets `PYTHONDONTWRITEBYTECODE=1`, so every pytest worker and every
`python -B -m ethos.cli` child compiles the standard library, the dependencies and `src` again
when it starts, and a fresh lane holds no compiled modules at all. The MCP conformance test starts
37 Python processes and spends about 40 % of its runtime on this repeated compilation.

## What Changes

- The test gate compiles the interpreter, environment, `src` and `tools` sources once per run into
  hash-checked bytecode under `build/runtime/tool-cache/python-bytecode`. It gives test processes
  that prefix only when every file compiled.
- Test processes keep `PYTHONDONTWRITEBYTECODE=1`. They read the shared bytecode and write none, so
  a module that a test generates always runs from its current source.

Out of scope: pytest's assertion-rewrite cache, the bytecode of materialized hook runtimes, which
run isolated, and test timeouts, worker counts and test order.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Shared bytecode changes no specified behavior; test outcomes and deadlines stay the same.

## Impact

The new `tools/ci/python_test_bytecode.py`, the prefix hand-off in `tools/ci/python_test_gate.py`,
the Nox `tests` session in `tools/ci/sessions.py` and a new architecture test. Each proof's
`unit-architecture` gate gains one parallel compile step and a lane-local cache under
`build/runtime/tool-cache/`. Writes stay under `build/`, so the unprivileged hosted test identity
keeps working.
