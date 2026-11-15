## MODIFIED Requirements

### Requirement: Group commands are catalog operations

Every `lane`, `hook`, `attestation` and `host` leaf SHALL be a catalog entry selected by its
command path and flags, with a kernel half in `ethos.contracts.operations` and an application half
in `ethos.application`; the surfaces SHALL hold no leaf body. `ethos mcp` SHALL remain a transport
launcher outside the catalog.

#### Scenario: A group request names a field its operation does not take

- **WHEN** a group leaf is run with a field outside its selected mode, such as `--authorize`
  without `--apply`
- **THEN** it runs nothing and exits 2 with `command_field_refused:<field>`
- **AND** a check that owns a body gap code, such as the retirement receipt, keeps that code

#### Scenario: A usage error names the full path

- **WHEN** a group leaf is run with a required field omitted
- **THEN** it exits 2 with `command_usage_invalid:<command path>` and a payload `command` equal to
  that path

#### Scenario: Help lists the catalog

- **WHEN** `ethos <path> --help` or `ethos <group> --help --json` is rendered
- **THEN** it prints that command's part of the catalog, or the group's own commands in full and
  its nested groups by name and help, within the declared help payload budget
- **AND** bare `ethos --help` lists no hidden group

#### Scenario: Host run exits with its child

- **WHEN** `ethos host run -- <command>` runs a command that the host admits
- **THEN** the entry's `process` exit makes the CLI exit with the child's status and print no frame
- **AND** an admission gap is emitted as a result like any other

#### Scenario: Host status is a read

- **WHEN** `ethos host status --json` runs
- **THEN** it selects `host.status`, whose only effect is `read`
- **AND** it exits 0 on every verdict
