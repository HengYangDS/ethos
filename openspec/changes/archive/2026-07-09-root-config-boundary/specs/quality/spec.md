## MODIFIED Requirements

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff and SHALL keep explicitly
frozen ignored-rule debt visible and non-increasing.

#### Scenario: Ruff gate blocks current hard rules and ignored-rule growth

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs Ruff check and Ruff format with explicit `.config/checks/ruff/ruff.toml`, plus the
  Ruff ignored-rule ratchet script
- **AND** each baseline in `.config/checks/ruff/ratchet.toml` is treated as a
  maximum, not a target
- **AND** a rule baseline may be lowered when findings are removed, but may not
  increase without an explicit quality debt decision

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and the configured hard coverage floor.

#### Scenario: default Python test gate is bounded and parallel-capable

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python test gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-tests.sh`
- **AND** pytest policy requires `pytest-timeout` and strict config/marker handling
- **AND** the owner script honors `ETHOS_TEST_WORKERS`, defaulting to parallel workers
- **AND** the owner script reports slow test durations and writes JUnit output under `build/evidence/quality/tests/pytest`
- **AND** pytest runtime cache lives under ignored `build/runtime/tool-cache/pytest`, not `.config/`
- **AND** benchmark and Allure reporting remain planned or opt-in unless admitted as active gates

### Requirement: Configuration and Script Quality Gates

ETHOS SHALL make configuration and runner-script quality executable through
reusable owner scripts rather than provider-specific CI inline policy, and the
same owner scripts SHALL participate in the default ETHOS proof floor.

#### Scenario: Python tool policy is owned outside the repository root

- **WHEN** the Python lint or Python test gate executes
- **THEN** ETHOS invokes the reusable owner scripts under `tools/ci/scripts/`
- **AND** Ruff policy is read from `.config/checks/ruff/ruff.toml`
- **AND** pytest configuration is read from `.config/checks/pytest/pytest.ini`
- **AND** the repository root does not contain `ruff.toml` or `pytest.ini`
- **AND** adopter CI scaffolds do not assume the product repository's Ruff, pytest,
  or owner-script surfaces

#### Scenario: Product docs may reference bounded owner scripts

- **WHEN** `ethos quality command-examples --json` scans active product docs
- **THEN** ETHOS admits documented `tools/ci/scripts/*.sh` examples as bounded
  repository-owned runner-script surfaces
- **AND** arbitrary `tools/**` command roots remain unknown command examples

#### Scenario: Coverage quality read model reports the active floor

- **WHEN** `ethos quality coverage --json` runs
- **THEN** ETHOS reports the coverage policy source, current hard floor, aspirational
  floor, branch coverage requirement, configured source paths, configured
  `fail_under`, owner script, and latest coverage artifact summary when present
- **AND** the command reports required gaps when policy or config is missing,
  `fail_under` diverges from the hard floor, branch coverage is disabled while
  required, the latest artifact is missing or malformed, or latest coverage is
  below the hard floor
- **AND** when the Python test owner script holds the coverage evidence write
  lock and the latest artifact is temporarily absent, the command reports the
  writer as in-progress advisory state rather than a stale coverage failure
- **AND** the command remains read-only and does not replace the reusable Python
  test gate owner script
