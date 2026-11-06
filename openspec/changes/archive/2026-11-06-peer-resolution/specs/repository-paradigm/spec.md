## ADDED Requirements

### Requirement: Retired publication fields are repaired, never ignored

The paradigm SHALL report `forge_repository`, `local_verification_command` and
`local_installation_command` in the publication declaration as retired. The report SHALL block
prove, land and publish, and SHALL NOT block `status`, `lane start`, prewrite,
`lane repair-paradigm` or commit. The repair SHALL derive from the carrier text alone, SHALL remove
the fields without echoing their values, and SHALL admit a declaration left without publication
fields as zero peers.

#### Scenario: A declaration still carries a retired field

- **WHEN** a repository's `release.toml` carries `forge_repository` or a local command field
- **THEN** the paradigm reports the retired field and names `ethos lane repair-paradigm --apply`
- **AND** `status` and prewrite still run

#### Scenario: The repair removes the fields without echoing values

- **WHEN** `lane repair-paradigm --apply` removes a retired `forge_repository`
- **THEN** its report names the field and the peer and never the value
- **AND** a second run changes nothing
