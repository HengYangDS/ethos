## MODIFIED Requirements

### Requirement: The behavior probe runs under the repository's native test configuration

The Python behavior probe SHALL run pytest with the repository's paradigm pytest carrier and the
repository root as rootdir, and SHALL measure coverage with its paradigm coverage carrier, when the
repository declares them. It SHALL run within its gate's deadline. A repository without these
carriers keeps pytest's native discovery and coverage of the whole tree.

#### Scenario: The paradigm carriers are declared

- **WHEN** a repository declares `.config/checks/pytest/pytest.toml` and
  `.config/checks/coverage/coverage.toml`
- **THEN** pytest collects and reports as the pytest carrier declares, with node identities relative
  to the repository root
- **AND** coverage uses the coverage carrier's source, branch, subprocess and floor settings, so a
  declared floor that is not met blocks the behavior evidence

#### Scenario: No carrier is declared

- **WHEN** a repository declares neither carrier
- **THEN** pytest discovers its own configuration and coverage measures the repository tree, as
  before

#### Scenario: A gate declares a longer timeout

- **WHEN** the gate that runs the probe declares `timeout_seconds` above 600
- **THEN** that value bounds the pytest run
- **AND** a gate that declares none runs within the repository's `timeout.gate_seconds`, 600 seconds
  unless the binding declares another value

## ADDED Requirements

### Requirement: Every gate runs under a recorded deadline

Each gate SHALL run under a deadline: its declared `timeout_seconds`, which SHALL stay within the
`timeout` group's bound, otherwise the repository's `timeout.gate_seconds`. A command inside a gate
SHALL run within that deadline. A proof SHALL record each gate's effective timeout with its source,
and every repository value looser than its default with the stated reason.

#### Scenario: An undeclared gate runs too long

- **WHEN** a gate without its own timeout runs longer than the repository's `timeout.gate_seconds`
- **THEN** it fails as `gate_timeout` with the timeout, its source and the elapsed time.

#### Scenario: A command inside a gate hangs

- **WHEN** a command inside a gate does not finish
- **THEN** the gate's deadline ends it, and the gate fails as `gate_timeout`.

#### Scenario: A gate declares a timeout beyond the bound

- **WHEN** a gate declares `timeout_seconds` above the `timeout.gate_seconds` bound
- **THEN** the repository profile reports the gate, and no proof runs it.

#### Scenario: A repository loosens a value

- **WHEN** a binding declares a higher value with a reason
- **THEN** the proof summary lists the parameter, its value, its default and the reason.
