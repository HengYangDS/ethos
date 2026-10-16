# Tasks

## 1. Shared Bytecode

- [x] 1.1 Compile shared bytecode in `tools/ci/python_test_bytecode.py` and hand its prefix to test processes through `PythonTestGate.compile_bytecode()`; verify `tests/architecture/test_python_test_bytecode.py` passes, and fails under timestamp invalidation and without `PYTHONDONTWRITEBYTECODE`.
- [x] 1.2 Compile before `run_tests` in the Nox `tests` session; verify `tests/architecture/test_python_test_gate.py`, `test_allure_reporting.py` and `test_release_assets.py` pass.
- [x] 1.3 Measure the MCP conformance workload with and without the gate's bytecode; verify each operation stays within its 30-second deadline and record the result as an observation Attestation (`bbc53dd1`).

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
