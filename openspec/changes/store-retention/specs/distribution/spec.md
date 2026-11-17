## ADDED Requirements

### Requirement: An absent consumer is released only by a previewed step

ETHOS SHALL release a recorded consumer whose repository path is absent only through
`ethos hook retire-supply --release-absent`: a preview that names every record it would release,
and an apply bound to that plan's digest and to an authorization. Only the host's answer that no
entry exists SHALL count as absence. The release SHALL unlink consumer records and SHALL NOT
remove an installation.

#### Scenario: The preview names what a release would do

- **WHEN** the preview runs with the switch over a scanned root
- **THEN** it lists each absent consumer's record with the consumer path, the installation and
  the bytes that the installation holds
- **AND** no record and no installation of the host store changes

#### Scenario: The host cannot look at a consumer's path

- **WHEN** reading a consumer's path fails for any reason other than a missing entry, such as a
  directory that may not be searched
- **THEN** the record is not planned
- **AND** no authorization releases it

#### Scenario: A repository moved

- **WHEN** a repository at a scanned root names an installation that an absent consumer recorded
- **THEN** the apply records that repository as a consumer before it unlinks any record
- **AND** the next cleanup keeps the installation

#### Scenario: An apply is refused

- **WHEN** the plan's digest is missing or differs from the store, or the authorization is absent
- **THEN** the apply refuses with `host_store_plan_required`, `host_store_plan_changed` or
  `authorization_required`
- **AND** it unlinks nothing

#### Scenario: A release is applied

- **WHEN** the apply runs with the previewed digest and the authorization
- **THEN** it unlinks each planned record whose path is still absent
- **AND** it removes no installation and names the cleanup of `ethos hook install` as the next
  step

#### Scenario: The switch is not given

- **WHEN** `ethos hook retire-supply` runs without `--release-absent`
- **THEN** no consumer record is planned or released
- **AND** its plan covers the installations that it covered before this requirement
