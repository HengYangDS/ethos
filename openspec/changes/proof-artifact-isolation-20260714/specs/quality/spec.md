## MODIFIED Requirements

### Requirement: Generated Artifact Topology Gate

ETHOS SHALL keep generated artifact placement auditable so source,
configuration, semantic documentation, repository root, runtime state,
generated proof output, and curated evidence remain distinct authority
surfaces.

#### Scenario: Root generated drift remains blocked while ignored test residue is local

- **WHEN** `ethos quality generated-artifacts --json` scans repository root paths
- **THEN** tracked or unignored generated outputs in repo root fail with
  `generated_artifact_repo_root_drift:<path>`
- **AND** ignored and untracked root `.coverage*`, `coverage.xml`, and `junit.xml`
  are reported as ignored local test residue rather than required gaps
- **AND** unrelated root generated outputs such as `proof.json` remain blocked
- **AND** the command remains read-only and does not clean files as part of the
  verdict

#### Scenario: Semantic generated homes are enforced

- **WHEN** `ethos quality generated-artifacts --json` scans ignored local state
- **THEN** root tool cache homes such as `.import_linter_cache/`,
  `.import-linter-cache/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`,
  `.tox/`, `.nox/`, `.uv-cache/`, and root `dist/` fail even when ignored
- **AND** retired flat generated homes such as `build/cache/` and
  `build/runtime/gitlab-ci-local/` fail
- **AND** allowed generated homes are semantic: `.cache/local-state/`,
  `.ethos/state/`, `build/runtime/tool-cache/<tool>/`,
  `build/runtime/work/<provider>/`, `build/evidence/`, `build/ethos/`, and
  `build/artifacts/<kind>/`
- **AND** the command reports lifecycle classes for `runtime_cache`,
  `machine_evidence`, `local_artifact`, and `curated_evidence`.

#### Scenario: Generated artifact producer entrypoints are audited

- **WHEN** `ethos quality generated-artifacts --json` runs
- **THEN** the command reports an `entrypoint_audit` over active CI projections,
  reusable owner scripts, package entrypoints, and tool configuration
- **AND** pytest entrypoints must use `.config/checks/pytest/pytest.ini`, route
  pytest cache to `build/runtime/tool-cache/pytest`, and write coverage/JUnit
  machine evidence under `build/evidence/quality/tests/`
- **AND** Ruff and import-linter entrypoints must route runtime cache under
  `build/runtime/tool-cache/ruff` and `build/runtime/tool-cache/import-linter`
- **AND** package build entrypoints must write to `build/artifacts/<kind>`
- **AND** `gitlab-ci-local` entrypoints must route provider state to
  `build/runtime/work/gitlab-ci-local`
- **AND** cleanup commands may remove denied residue but do not make a producer
  that recreates denied homes compliant.

#### Scenario: Product proof seals topology after runtime-producing gates

- **WHEN** the default product proof executes its quality gates
- **THEN** `generated-artifacts` runs after the Ruff and Python test gates
- **AND** root `.pytest_cache/` and `.ruff_cache/` remain denied at the final
  topology verdict
- **AND** the Python test gate removes those denied root caches at both entry
  and EXIT cleanup
- **AND** standalone `ethos quality generated-artifacts --json` remains
  read-only and fails closed on surviving root cache drift.

#### Scenario: Runtime-producing quality owners stay semantically bound and portable

- **WHEN** the product runs its type, lint, Ruff-ratchet, or Bandit owner
  gates from a governed checkout
- **THEN** `ty` resolves third-party imports against
  `build/runtime/venv`, never an ambient host or root `.venv`
- **AND** each owner gate preserves its tracked Python-file scope under the
  macOS-provided Bash 3.2
- **AND** no owner gate requires a newer shell or silently weakens its file
  selection to obtain portability.
