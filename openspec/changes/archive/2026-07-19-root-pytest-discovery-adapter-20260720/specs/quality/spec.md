## MODIFIED Requirements

### Requirement: Configuration and Script Quality Gates

ETHOS SHALL make configuration and runner-script quality executable through
reusable owner scripts rather than provider-specific CI inline policy, and the
same owner scripts SHALL participate in the default ETHOS proof floor.

#### Scenario: Python tool policy is owned outside the repository root

- **WHEN** the Python lint or Python test gate executes
- **THEN** ETHOS invokes the reusable owner scripts under `tools/ci/scripts/`
- **AND** Ruff policy is read from `.config/checks/ruff/ruff.toml`
- **AND** pytest configuration is read from `.config/checks/pytest/pytest.ini`
- **AND** root `pyproject.toml` carries only the pytest discovery cache route to
  `build/runtime/tool-cache/pytest`
- **AND** the repository root does not contain `ruff.toml` or `pytest.ini`
- **AND** adopter CI scaffolds do not assume the product repository's Ruff,
  pytest, or owner-script surfaces

#### Scenario: Bare pytest discovery preserves the semantic cache boundary

- **WHEN** a human or IDE invokes pytest from the repository root without the
  repository owner script
- **THEN** pytest discovers only the root cache route and writes cache under
  `build/runtime/tool-cache/pytest`
- **AND** the invocation does not gain owner-script test selection, strictness,
  coverage, JUnit, or proof semantics
- **AND** the invocation does not create root `.pytest_cache`

#### Scenario: Product docs may reference bounded owner scripts

- **WHEN** `ethos quality command-examples --json` scans active product docs
- **THEN** ETHOS admits documented `tools/ci/scripts/*.sh` examples as bounded
  repository-owned runner-script surfaces
- **AND** arbitrary `tools/**` command roots remain unknown command examples

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
  docstring, module-layout, Python size, unit/coverage, and format-policy gates
- **AND** CI, pre-commit, and proof invoke reusable owner scripts instead of
  copying tool command policy into provider projections

#### Scenario: Report exposes hard quality-floor gaps

- **WHEN** a product hard quality gate such as Python size, module layout,
  coverage, type policy, or public-surface docstrings reports required gaps
- **THEN** `ethos report --json` includes those gaps in its blocking
  `required_gaps`
- **AND** the report state is not ready
- **AND** the report payload includes a `hard_quality_floor` read model with the
  contributing gate verdicts
- **AND** next actions point to the concrete standalone quality command instead
  of implying full proof can close the gap

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
