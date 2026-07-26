## MODIFIED Requirements

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and the configured hard coverage floor. The owner
script SHALL accept optional paired timeout-seconds/timeout-method and
run-as-UID/run-as-GID inputs, validate either pair before test execution, and
otherwise preserve the repository-wide pytest defaults and caller identity.

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
  test owner script
- **THEN** the provider projection uses two workers to bound simultaneous
  subprocess and Git pressure while preserving parallel execution
- **AND** the provider projection sets a 300-second signal timeout through the
  validated paired owner-script inputs
- **AND** a timeout is reported as a pytest test failure rather than an abrupt
  xdist worker exit
- **AND** GitLab and callers without the paired inputs retain the repository-wide
  defaults
- **AND** missing, non-positive, or unsupported override values fail before test
  execution.

#### Scenario: GitLab Docker proof preserves root bootstrap and truthful worker isolation

- **GIVEN** the GitLab Docker executor launches `python:3.14` as root so bootstrap
  can install the pinned Node runtime and maintain persistent root-owned caches
- **WHEN** the `ethos:verify` job reaches the Python test owner script
- **THEN** GitLab supplies the complete numeric UID/GID pair `65534:65534`
- **AND** the owner script requires a root launcher and `setpriv`, prepares only
  generated `build/` and temporary test paths for that identity, and runs pytest
  with cleared supplementary groups
- **AND** before returning to later root-owned job stages, the owner script
  restores root ownership of generated build and pytest temporary paths
- **AND** the run-as pair is consumed before pytest so nested owner-script calls
  remain unprivileged without attempting a second root-only drop
- **AND** the test process retains only exact safe-directory overlays for the
  checkout root and `.git`, plus the fsmonitor-disable overlay
- **AND** the source-budget worker still fails closed if UID 0 or prohibited
  capabilities remain
- **AND** a missing, partial, zero, non-decimal, non-root, or unavailable-`setpriv`
  identity request fails before pytest execution
- **AND** the complete Linux gate SHALL independently exercise platform adapter
  contracts and satisfy the configured 100% branch-coverage floor.
