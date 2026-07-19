## RENAMED Requirements

- FROM: `Python Lint and Format Ratchet`
- TO: `Python Lint and Format`

## MODIFIED Requirements

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff. Every selected rule
applicable to every tracked Python asset SHALL report zero findings; a global
ignore list, per-file ignore, ratchet, historical baseline, or source-level
suppression SHALL not satisfy the quality law.

#### Scenario: Ruff gate blocks every selected rule

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs Ruff check and Ruff format with explicit
  `.config/checks/ruff/ruff.toml`
- **AND** Ruff runtime cache lives under ignored `build/runtime/tool-cache/ruff`, not root `.ruff_cache/`
- **AND** Ruff check and Ruff format use the same tracked Python file set, so
  packages, tools, tests, agent scripts, and CI adapters obey one
  repository-wide Python law
- **AND** each selected finding blocks the owner script directly rather than
  being represented by a baseline, debt record, waiver, or compatibility surface

#### Scenario: Type checks use a checkout-bound runtime without ambient venv noise

- **WHEN** `ethos quality types --json` checks a governed package from a Work Lane
- **THEN** the type adapter invokes the checkout-local runtime wrapper before
  `uv run --locked --all-packages --group dev python -m ty`
- **AND** the wrapper binds the runtime to `build/runtime/venv` for that checkout
- **AND** an inherited `VIRTUAL_ENV` neither redirects resolution nor emits a
  false active-environment mismatch warning

#### Scenario: Ruff gate blocks current hard rules and ignored-rule growth

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs Ruff check and Ruff format with explicit
  `.config/checks/ruff/ruff.toml`
- **AND** Ruff runtime cache lives under ignored `build/runtime/tool-cache/ruff`, not root `.ruff_cache/`
- **AND** Ruff check and Ruff format use the same tracked Python file set, so
  packages, tools, tests, agent scripts, and CI adapters obey one
  repository-wide Python law
- **AND** each selected finding blocks the owner script directly rather than
  being represented by a baseline, debt record, waiver, or compatibility surface

#### Scenario: A retained exception carrier blocks proof

- **WHEN** policy declares a Ruff ignore, per-file ignore, ratchet, `noqa`, or
  equivalent source suppression for a governed asset
- **THEN** the quality contract reports a required gap
- **AND** the default proof graph blocks

#### Scenario: A projection invokes Python quality

- **WHEN** a local command, pre-commit hook, hosted CI job, or proof graph
  invokes Python quality
- **THEN** it reaches the same repository-owned Ruff policy and owner script
- **AND** no projection supplies a separate rule set or tolerated count
