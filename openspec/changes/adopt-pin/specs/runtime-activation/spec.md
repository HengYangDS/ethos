## MODIFIED Requirements

### Requirement: A repository exit is previewed before any effect

`ethos adopt --exit` SHALL report, without any effect, the configuration after the exit per key, the
keys it keeps because ETHOS no longer owns them, the keys it leaves unrecorded, the record entries
it cannot restore, the generations it removes and keeps, the selectors with their hashes, the Leases
and unlanded branches, the Mise pin it removes, and a digest over them. It SHALL resume an
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

- **WHEN** the Mise configuration of an adopted repository holds the bare ETHOS pin
- **THEN** the preview names that file, the pin's key and the file's text without the pin's line
- **AND** the provenance setting and a pin in any other form are not part of the plan

### Requirement: A previewed exit is applied in a fenced order

With `--apply`, `--authorize`, the current head and the previewed digest, the exit SHALL, under the
runtime selection lock and a state write transaction, write a durable receipt, remove the record,
restore each key that still holds ETHOS's value, verify that no worktree uses ETHOS's hooks, remove
each selector that still holds its planned bytes and the planned Mise pin, and mark the receipt
applied. A failure SHALL attempt every compensation step and report any that fails.

#### Scenario: An adopted repository exits

- **GIVEN** a repository with its own hooks path that adopted ETHOS
- **WHEN** the exit is applied with the previewed digest
- **THEN** the hooks path is its own again and no selector remains
- **AND** the receipt holds the selector hashes and the configuration before and after.

#### Scenario: The plan changed after the preview

- **WHEN** a key, a selector or a blocker changes between the preview and the apply
- **THEN** the exit is refused and nothing changes.

#### Scenario: An exit fails after restoring the configuration

- **WHEN** a step after the receipt fails
- **THEN** every compensation step is attempted
- **AND** the result is `unknown` when one of them fails.

#### Scenario: An exit removes the pin that adoption wrote

- **GIVEN** a repository whose Mise configuration holds the bare ETHOS pin beside its own tools
- **WHEN** the exit is applied with the previewed digest
- **THEN** that file loses the pin's line and keeps every other line, the provenance setting
  included
- **AND** no other tracked file changes
