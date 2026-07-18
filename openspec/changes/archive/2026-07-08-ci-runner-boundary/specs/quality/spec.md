## MODIFIED Requirements

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff and SHALL keep explicitly
frozen ignored-rule debt visible and non-increasing.

#### Scenario: Ruff gate blocks current hard rules and ignored-rule growth

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs `ruff check .`, `ruff format --check .`, and the
  Ruff ignored-rule ratchet script
- **AND** each baseline in `.config/checks/ruff/ratchet.toml` is treated as a
  maximum, not a target
- **AND** a rule baseline may be lowered when findings are removed, but may not
  increase without an explicit quality debt decision

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and an explicit 95 percent hard coverage floor.

#### Scenario: default Python test gate is bounded and parallel-capable

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python test gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-tests.sh`
- **AND** pytest policy requires `pytest-timeout` and strict config/marker handling
- **AND** the owner script honors `ETHOS_TEST_WORKERS`, defaulting to parallel workers
- **AND** the owner script reports slow test durations and writes JUnit output under `.config/checks/pytest`
- **AND** benchmark and Allure reporting remain planned or opt-in unless admitted as active gates

### Requirement: Python Module Layout Gate

ETHOS SHALL gate Python module layout as a quality property so semantic
sub-packages, package-root visibility, suffix-flat debt, flat-directory debt,
ordinary-module facade debt, same-directory flat-growth, baseline growth, and
import-alias compatibility residue cannot grow through normal write paths.

#### Scenario: Semantic module layout is reported and enforced

- **WHEN** `ethos quality module-layout --json` runs
- **THEN** ETHOS reports suffix-module, suffix-flat, flat-directory, private import
  alias, package `__init__.py` facade, ordinary module facade, flat-growth, and
  baseline-growth findings against `.config/checks/module-layout/policy.toml`
- **AND** hosted CI, pre-commit, local CI, and proof invoke the reusable
  `tools/ci/scripts/run-module-layout.sh` owner script instead of duplicating
  the policy inline.
