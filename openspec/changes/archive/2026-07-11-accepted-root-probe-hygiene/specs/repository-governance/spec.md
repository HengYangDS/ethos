## ADDED Requirements

### Requirement: Temporary test probe provenance remains explicit and bounded

ETHOS SHALL classify a dirty entry as a temporary test probe only when Git
reports it as untracked, its repository-relative path is under `tests/`, its
basename matches `test_*.py`, and its bounded file header contains the literal
`TEMP PROBE`. Workspace status SHALL expose a `temporary_probes` summary with
an exact count, a bounded list of repository-relative paths, and an overflow
indicator. The summary SHALL be present for clean, dirty, unavailable, and
non-Git provenance payloads.

#### Scenario: Explicit untracked probe is recognized

- **WHEN** an accepted or candidate checkout contains an untracked
  `tests/**/test_*.py` file whose header contains `TEMP PROBE`
- **THEN** workspace status includes that file in `dirty_provenance.temporary_probes`
- **AND** the summary count and path list identify the probe without changing
  the Git dirty entries

#### Scenario: Ordinary untracked files are not misclassified

- **WHEN** a dirty checkout contains an untracked file outside `tests/`, a
  non-test Python file, or a test file without the header marker
- **THEN** its ordinary dirty provenance remains visible
- **AND** `temporary_probes` does not classify that file as a probe

#### Scenario: Probe list remains bounded

- **WHEN** more temporary probes exist than the path-list bound
- **THEN** the summary reports the exact total count
- **AND** it reports a bounded repository-relative path list and an overflow
  indicator

### Requirement: Protected-root probe remediation is reader-only

ETHOS SHALL derive explicit temporary-probe remediation in orientation when an
accepted or candidate root has one or more classified temporary probes. The
JSON and human orientation views SHALL state that the operator must remove the
probe or migrate it into an owned Work Lane, and SHALL state that no automated
cleanup occurs. The projection SHALL NOT mint authority to write, land,
retire, or clean another lane.

#### Scenario: Accepted root receives explicit remediation

- **WHEN** `ethos orient --json` reads an accepted root with classified
  temporary probes
- **THEN** its candidate action names temporary-probe removal or migration
- **AND** its reason and next actions identify removal or migration into an
  owned Work Lane
- **AND** its mutation and landing capabilities remain false

#### Scenario: Ordinary dirty state keeps its existing orientation

- **WHEN** a protected root is dirty but has no classified temporary probe
- **THEN** orientation retains the generic dirty-state candidate action and
  remediation
- **AND** no temporary-probe remediation is implied
