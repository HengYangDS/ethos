## MODIFIED Requirements

### Requirement: Python Lint and Format Ratchet

ETHOS SHALL enforce Python lint and format through Ruff and SHALL keep
explicitly frozen ignored-rule debt visible and non-increasing. A rule whose
finding count reaches zero SHALL leave both the ignore set and ratchet,
returning to direct enforcement.

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

#### Scenario: An eliminated unused-method-argument rule returns to direct enforcement

- **WHEN** the Python quality policy and owner lint gate run against all tracked
  Python files
- **THEN** the corpus reports zero `ARG002` findings
- **AND** `ARG002` is absent from the Ruff global ignore list and ratchet
  baseline
- **AND** any future `ARG002` finding fails the canonical Ruff owner gate
- **AND** no alternate command, baseline, or compatibility policy accepts it

#### Scenario: Dry-run actions bind their declared execution root

- **WHEN** `DryRunRunner` plans an action with a repository root
- **THEN** it resolves that root without executing the action
- **AND** it returns a planned action result
