## ADDED Requirements

### Requirement: Process exits follow one declared table

The kernel SHALL declare every process exit the command plane uses as one table of exit kinds
with their numbers: `pass` 0, `blocked` 1, `usage` 2, `undelivered` 3, `process` carrying the
child's status, and `refused` 125 reserved for a refusal apart from the child's failure. A CLI
exit SHALL read its number from the table by kind, and `ethos --help --json` SHALL print the table
with each row's number, meaning and reservation.

#### Scenario: Help prints the exit table

- **WHEN** `ethos --help --json` runs
- **THEN** `data.exits` lists every kind with its status, meaning and reserved flag
- **AND** `refused` carries 125 with `reserved` true

#### Scenario: A usage refusal exits by the table

- **WHEN** a request does not parse
- **THEN** the process exits 2, read from the `usage` row rather than a literal
