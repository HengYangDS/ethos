## MODIFIED Requirements

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and an explicit 95 percent hard coverage floor.

#### Scenario: default Python test gate is bounded and parallel-capable

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python test gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-tests.sh`
- **AND** pytest policy requires `pytest-timeout` and strict config/marker handling
- **AND** the owner script honors `ETHOS_TEST_WORKERS`, defaulting to parallel workers
- **AND** the owner script reports slow test durations and writes JUnit output under `build/evidence/quality/tests/pytest`
- **AND** pytest runtime cache lives under ignored `build/runtime/tool-cache/pytest`, not `.config/`
- **AND** benchmark and Allure reporting remain planned or opt-in unless admitted as active gates
