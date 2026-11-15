## MODIFIED Requirements

### Requirement: A repository exit is previewed before any effect

`ethos adopt --exit` SHALL report, without any effect, the configuration after the exit per key, the
keys it keeps because ETHOS no longer owns them, the keys it leaves unrecorded, the record entries
it cannot restore, the generations it removes and keeps, the selectors with their hashes, the Leases
and unlanded branches, the Mise pin it removes or keeps, and a digest over them. It SHALL resume an
interrupted exit from its receipt.

#### Scenario: An exit is inspected

- **WHEN** `ethos adopt --exit --json` runs in an adopted repository with a recorded configuration
- **THEN** it reports the configuration after the exit, the selector hashes and a plan digest
- **AND** no file, configuration or selector changes.

#### Scenario: A key changed after adoption

- **WHEN** a hooks path set after adoption no longer names ETHOS's hooks
- **THEN** the preview keeps it and reports it as kept.

#### Scenario: A repository is not adopted

- **WHEN** the repository has no runtime selector, no hooks path that ETHOS owns and no interrupted
  exit
- **THEN** the exit reports `adoption_exit_not_adopted` and plans no effect
- **AND** it reads no hand-made file as a record.

#### Scenario: An exit was interrupted

- **WHEN** an exit's receipt is still applying
- **THEN** the preview plans the remaining steps from that receipt.

#### Scenario: No configuration was recorded

- **WHEN** the repository was adopted before installation recorded its configuration
- **AND** its hooks path is still ETHOS's
- **THEN** the exit's next action names the Git commands that settle the hooks path.

#### Scenario: A lane holds a live Lease

- **WHEN** a Work Lane of the repository holds a valid Lease
- **THEN** the exit preview names that Lease as a blocker
- **AND** its plan digest differs from one made before the Lease.

#### Scenario: A running process uses the runtime

- **WHEN** a process other than the exit's own refers to the repository's runtime or hooks
  generations
- **THEN** the exit preview names `adoption_exit_runtime_in_use` as a blocker.

#### Scenario: The Mise configuration holds the pin that adoption wrote

- **WHEN** the Mise configuration of an adopted repository holds the bare ETHOS pin on a line of
  its own under `[tools]`
- **THEN** the preview names that file, the pin's key and the file's text without the pin's line
- **AND** the provenance setting and a pin in any other form are not part of the plan

#### Scenario: The exit keeps a Mise configuration it cannot change exactly

- **WHEN** the Mise configuration of an adopted repository cannot be read, or holds the bare ETHOS
  pin other than on a line of its own
- **THEN** the preview names that file as kept with the reason, and the pin's key where it read one
- **AND** the apply leaves that file as it is
- **AND** a repository without that file plans no pin
