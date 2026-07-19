## MODIFIED Requirements

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff and SHALL keep explicitly
frozen ignored-rule debt visible and non-increasing. A rule whose finding count
reaches zero SHALL leave both the ignore set and ratchet, returning to direct
enforcement.

#### Scenario: Ruff gate blocks current hard rules and ignored-rule growth

- **WHEN** hosted CI or `ethos prove --execute --json` runs the Python lint gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-python-lint.sh`
- **AND** that owner script runs Ruff check and Ruff format with explicit
  `.config/checks/ruff/ruff.toml`, plus the Ruff ignored-rule ratchet script
- **AND** Ruff runtime cache lives under ignored `build/runtime/tool-cache/ruff`, not root `.ruff_cache/`
- **AND** the Ruff ratchet uses the same tracked Python file set as Ruff check and
  Ruff format, so packages, tools, tests, agent scripts, and CI adapters obey one
  repository-wide Python law
- **AND** each baseline in `.config/checks/ruff/ratchet.toml` must equal the
  current finding count for that ignored rule, not a slack maximum
- **AND** the gate fails both when findings exceed a baseline and when findings
  fall below a stale baseline, forcing debt reductions to be recorded
- **AND** a rule whose finding count reaches zero is removed from the ignored-rule
  ratchet and returns to the hard Ruff rule set
- **AND** a rule baseline may be lowered when findings are removed, but may not
  increase without an explicit quality debt decision

#### Scenario: A zero-finding temporal rule returns to direct enforcement

- **WHEN** the policy-exception clock uses an explicit UTC calendar boundary
- **THEN** the whole tracked Python corpus reports zero `DTZ011` findings
- **AND** `DTZ011` is absent from the Ruff ignore list and ratchet baseline
- **AND** any future `DTZ011` finding blocks the ordinary Ruff owner script

### Requirement: Zero-Tolerance Python Type Policy

ETHOS SHALL enforce Python type checking as a fail-closed, zero-diagnostic
quality gate for every package declared by `.config/checks/ty/policy.toml`.
The policy SHALL contain no type-diagnostic ratchet, baseline, ignore, or
exception once a package is governed by this requirement.

#### Scenario: Unknown type-tool execution blocks proof

- **WHEN** `ty` is unavailable, cannot launch, exits without a terminal
  diagnostic result, or produces malformed terminal output
- **THEN** `ethos quality types --json` reports a stable required execution gap
- **AND** the command exits non-zero through its enforced quality verdict
- **AND** the result does not report the unknown execution as zero diagnostics

#### Scenario: Every declared package has zero diagnostics

- **WHEN** `ethos quality types --json` runs with an available `ty` runtime
- **THEN** every package declared in the zero-tolerance policy reports
  `tier = "zero_tolerance"` and `limit = 0`
- **AND** any positive diagnostic count reports
  `ty_zero_tolerance_violation:<package>:<count>`
- **AND** CI and the default proof graph invoke the same owner gate

#### Scenario: Retired type debt cannot return as a baseline

- **WHEN** all governed packages report zero diagnostics
- **THEN** the type policy contains no ratchet table or equivalent exception
- **AND** a future diagnostic blocks immediately rather than establishing a
  new tolerated count

#### Scenario: Type checks use a checkout-bound runtime without ambient venv noise

- **WHEN** `ethos quality types --json` checks a governed package from a Work Lane
- **THEN** the type adapter invokes the checkout-local runtime wrapper before
  `uv run --locked --all-packages --group dev python -m ty`
- **AND** the wrapper binds the runtime to `build/runtime/venv` for that checkout
- **AND** an inherited `VIRTUAL_ENV` neither redirects resolution nor emits a
  false active-environment mismatch warning
