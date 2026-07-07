# ETHOS Quality

## Purpose

ETHOS SHALL define quality, determinism, documentation quality, proof policy,
and asset-governance semantics as a first-class product capability.
## Requirements
### Requirement: Quality Asset Model

ETHOS SHALL model repository assets across code, docs, shell, configuration,
evidence, release artifacts, and adopter profiles.

#### Scenario: Asset policy is reported

- **WHEN** `ethos quality asset-policy --json` runs
- **THEN** ETHOS reports asset classes, dimensions, and mature tool adapter
  profiles without executing provider tools

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff and SHALL keep explicitly
frozen ignored-rule debt visible and non-increasing.

#### Scenario: Ruff gate blocks current hard rules and ignored-rule growth

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `.config/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs `ruff check .`, `ruff format --check .`, and the
  Ruff ignored-rule ratchet script
- **AND** each baseline in `.config/checks/ruff/ratchet.toml` is treated as a
  maximum, not a target
- **AND** a rule baseline may be lowered when findings are removed, but may not
  increase without an explicit quality debt decision

### Requirement: Gate Descriptor Model

ETHOS SHALL describe quality gates with asset classes, dimensions, execution
mode, evidence class, trust-bearing classification, tool adapter, file-write
policy, network policy, and version source.

#### Scenario: Gate descriptors are reported

- **WHEN** `ethos quality gates --json` runs
- **THEN** every gate includes the quality descriptor fields required by the
  gate schema

### Requirement: Proof Policy Lattice

ETHOS SHALL distinguish planned, readiness, executed, proven, blocked,
accepted-risk, and waived-nonblocking proof states.

#### Scenario: Trust-bearing consumers require proven evidence

- **WHEN** `ethos quality proof-policy --json` runs
- **THEN** only `proven` is marked trust-bearing for claim, land, publish,
  release, and repository governance consumers

### Requirement: Documentation Quality Profile

ETHOS SHALL make documentation faithfulness, expressiveness, and elegance
mechanically checkable through metadata, visible reader sections, glossary,
links, anchors, and command examples.

#### Scenario: Docs profile is reported

- **WHEN** `ethos quality docs --json` runs
- **THEN** ETHOS reports docs quality profile checks alongside current docs
  registry health

### Requirement: Parallel Timeout-Bound Test Gate

ETHOS SHALL run the default Python test gate through a reusable owner script that
supports bounded parallel execution, timeout protection, slow-test visibility,
JUnit output, branch coverage, and an explicit 95 percent hard coverage floor.

#### Scenario: default Python test gate is bounded and parallel-capable

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python test gate
- **THEN** ETHOS invokes `.config/ci/scripts/run-python-tests.sh`
- **AND** pytest policy requires `pytest-timeout` and strict config/marker handling
- **AND** the owner script honors `ETHOS_TEST_WORKERS`, defaulting to parallel workers
- **AND** the owner script reports slow test durations and writes JUnit output under `.config/checks/pytest`
- **AND** benchmark and Allure reporting remain planned or opt-in unless admitted as active gates

### Requirement: Configuration and Script Quality Gates

ETHOS SHALL make configuration and runner-script quality executable through
reusable owner scripts rather than provider-specific CI inline policy, and the
same owner scripts SHALL participate in the default ETHOS proof floor.

#### Scenario: TOML and YAML configuration gates execute through owner scripts

- **WHEN** hosted CI or `ethos quality toml --json` / `ethos quality yaml --json` runs
- **THEN** ETHOS invokes the reusable configuration lint script
- **AND** TOML files are parsed, checked for exactly one final newline, checked
  for trailing whitespace, formatted with the configured Taplo policy, and linted
  with Taplo
- **AND** YAML files are linted with the configured Yamllint policy
- **AND** `.gitlab-ci.yml` does not duplicate Taplo or Yamllint policy inline

#### Scenario: Shell quality executes through the owner script

- **WHEN** hosted CI or `ethos quality shell --json` runs
- **THEN** ETHOS invokes the reusable shell lint script
- **AND** ShellCheck policy is read from `.config/checks/shell/.shellcheckrc`
- **AND** `.gitlab-ci.yml` does not duplicate ShellCheck policy inline

#### Scenario: Tool catalog exposes active configuration gates

- **WHEN** `system/tools.toml` is inspected
- **THEN** TOML, YAML, and shell concerns are marked active with their owning
  config path and reusable gate script
- **AND** planned tool entries do not masquerade as active gates

#### Scenario: Default proof consumes the active quality floor

- **WHEN** `ethos prove --json` builds its default action graph
- **THEN** the graph includes TOML, YAML, shell, Python lint, Python type,
  docstring, unit/coverage, and format-policy gates
- **AND** CI, pre-commit, and proof invoke reusable owner scripts instead of
  copying tool command policy into provider projections

#### Scenario: Coverage quality read model reports the active floor

- **WHEN** `ethos quality coverage --json` runs
- **THEN** ETHOS reports the coverage policy source, hard floor, aspirational
  floor, branch coverage requirement, configured source paths, configured
  `fail_under`, owner script, and latest coverage artifact summary when present
- **AND** the command reports required gaps when policy or config is missing,
  `fail_under` diverges from the hard floor, branch coverage is disabled while
  required, the latest artifact is missing or malformed, or latest coverage is
  below the hard floor
- **AND** the command remains read-only and does not replace the reusable Python
  test gate owner script


### Requirement: Python Module Layout Gate

ETHOS SHALL gate Python module layout as a quality property so semantic
sub-packages, package-root visibility, suffix-flat debt, flat-directory debt,
and import-alias compatibility residue cannot grow through normal write paths.

#### Scenario: Semantic module layout is reported and enforced

- **WHEN** `ethos quality module-layout --json` runs
- **THEN** ETHOS reports suffix-module, suffix-flat, flat-directory, private import
  alias, and package `__init__.py` facade findings against
  `.config/checks/module-layout/policy.toml`
- **AND** new findings outside the ratchet baseline fail the gate
- **AND** the ratchet baseline declares `baseline_gap_limit`, fails unless the
  current allowed-baseline count exactly matches that limit, and fails when
  baseline entries no longer correspond to current findings
- **AND** package-root `__init__.py` files remain declaration-only docstring
  boundaries rather than re-export or compatibility facades
- **AND** hosted CI, pre-commit, local CI, and proof invoke the reusable
  `.config/ci/scripts/run-module-layout.sh` owner script instead of duplicating
  the policy inline.

### Requirement: Python Public-Surface Docstring Gate

ETHOS SHALL gate intent-bearing Google-style docstrings for public Python product surfaces
without requiring private helper docstrings to become a parallel documentation
store.

#### Scenario: Public docstring coverage is reported

- **WHEN** `ethos quality docstrings --json` runs
- **THEN** ETHOS reports configured source paths, minimum coverage, documented
  public-surface count, total public-surface count, missing symbols, Google-style
  conformance, and a non-blocking broader public-definition inventory
- **AND** the gate fails when public-surface coverage is below the configured
  threshold
- **AND** existing structured docstrings must use Google-style sections and their
  `Args` section must match the Python signature
- **AND** legacy reStructuredText or NumPy-style sections are rejected
- **AND** the gate scope is limited to product-visible Python surfaces such as
  CLI command functions, explicit exports, and package boundary docstrings
- **AND** hosted CI invokes the reusable docstring coverage script instead of
  duplicating the policy inline.

