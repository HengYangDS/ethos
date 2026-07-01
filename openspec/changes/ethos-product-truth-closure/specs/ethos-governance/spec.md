## ADDED Requirements

### Requirement: Honest Product Migration State
ETHOS SHALL distinguish physical target package homes from completed migration.

#### Scenario: Target homes exist while migration hosts remain active
- **WHEN** ETHOS audits package ontology
- **THEN** target product packages and migration hosts are disjoint
- **AND** migration state is reported as `in_progress`
- **AND** migration is not reported complete until migration hosts are frozen,
  moved, or retired through parity evidence

### Requirement: Command Example Self-Governance
ETHOS SHALL validate current documentation command examples against the public
command plane.

#### Scenario: Unknown ETHOS subcommand appears in current docs
- **WHEN** `ethos quality command-examples --json` scans current docs
- **THEN** it reports an `unknown_ethos_command_example` gap

#### Scenario: Required product examples are absent
- **WHEN** key proof or command-example governance examples are absent
- **THEN** it reports `missing_command_example` gaps
