## MODIFIED Requirements

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and the configured hard coverage floor. The owner
script SHALL accept an optional paired timeout-seconds and timeout-method
override, validate it before test execution, and otherwise preserve the
repository-wide pytest defaults.

#### Scenario: default Python test gate is bounded and parallel-capable

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python test gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-tests.sh`
- **AND** pytest policy requires `pytest-timeout` and strict config/marker handling
- **AND** the owner script honors `ETHOS_TEST_WORKERS`, defaulting to parallel workers
- **AND** the owner script reports slow test durations and writes JUnit output under `build/evidence/quality/tests/pytest`
- **AND** pytest runtime cache lives under ignored `build/runtime/tool-cache/pytest`, not `.config/`
- **AND** benchmark and Allure reporting remain planned or opt-in unless admitted as active gates

#### Scenario: hosted macOS proof requires observable timeout failure

- **GIVEN** the repository-wide pytest default remains 120 seconds with thread
  timeout handling
- **WHEN** the self-hosted macOS GitHub repository-proof job invokes the Python
  test owner script with four workers
- **THEN** the provider projection sets a 300-second signal timeout through the
  validated paired owner-script inputs
- **AND** a timeout is reported as a pytest test failure rather than an abrupt
  xdist worker exit
- **AND** GitLab and callers without the paired inputs retain the repository-wide
  defaults
- **AND** missing, non-positive, or unsupported override values fail before test
  execution.
