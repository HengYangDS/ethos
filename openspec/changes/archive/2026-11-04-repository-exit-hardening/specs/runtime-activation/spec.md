## MODIFIED Requirements

### Requirement: Installation records the configuration it replaces

When `ethos hook install` replaces a value that ETHOS does not own, it SHALL record that value, per key, in the common and worktree scopes, and an absent value as absent. It SHALL NOT record a value that ETHOS owns, current or legacy, SHALL keep the recorded entry of a key it already owns, and SHALL write the record and clear an earlier exit's receipt within the activation, restoring both if the activation fails.

#### Scenario: A repository with its own hooks adopts ETHOS

- **GIVEN** a repository whose `core.hooksPath` names its own hooks directory
- **WHEN** `ethos hook install` activates a runtime
- **THEN** the record names that hooks path
- **AND** a later upgrade leaves the record unchanged.

#### Scenario: A repository without a hooks path adopts ETHOS

- **WHEN** `ethos hook install` activates a runtime in a repository without `core.hooksPath`
- **THEN** the record holds the hooks path as absent.

#### Scenario: A legacy ETHOS hooks path is replaced

- **WHEN** install replaces a worktree's `core.hooksPath` that names a legacy ETHOS hooks directory
- **THEN** the record holds no entry for that value.

#### Scenario: A repository adopts ETHOS again

- **GIVEN** a repository whose hooks path changed after an earlier adoption or exit
- **WHEN** `ethos hook install` activates a runtime
- **THEN** the record names the new hooks path
- **AND** no earlier exit receipt remains.

### Requirement: A repository exit is previewed before any effect

`ethos adopt --exit` SHALL report, without any effect, the configuration after the exit per key, the keys it keeps because ETHOS no longer owns them, the keys it leaves unrecorded, the record entries it cannot restore, the generations it removes and keeps, the selectors with their hashes, the Leases and unlanded branches, and a digest over them. It SHALL resume an interrupted exit from its receipt.

#### Scenario: An exit is inspected

- **WHEN** `ethos adopt --exit --json` runs in an adopted repository with a recorded configuration
- **THEN** it reports the configuration after the exit, the selector hashes and a plan digest
- **AND** no file, configuration or selector changes.

#### Scenario: A key changed after adoption

- **WHEN** a hooks path set after adoption no longer names ETHOS's hooks
- **THEN** the preview keeps it and reports it as kept.

#### Scenario: A repository is not adopted

- **WHEN** the repository has no runtime selector, no hooks path that ETHOS owns and no
  interrupted exit
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

### Requirement: A previewed exit is applied in a fenced order

With `--apply`, `--authorize`, the current head and the previewed digest, the exit SHALL, under the runtime selection lock and a state write transaction, write a durable receipt, remove the record, restore each key that still holds ETHOS's value, verify that no worktree uses ETHOS's hooks, remove each selector that still holds its planned bytes, and mark the receipt applied. A failure SHALL attempt every compensation step and report any that fails.

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

### Requirement: Status reports an exit

Status SHALL report an applied exit while no runtime is selected, and an interrupted exit whenever its receipt remains, and a repository without a repository profile SHALL NOT require hooks once it has exited.

#### Scenario: Status after an exit

- **WHEN** status runs in a repository that exited
- **THEN** it reports the exit and its receipt.

#### Scenario: Status after an interrupted exit

- **WHEN** an exit stopped before it marked its receipt applied
- **THEN** status reports the exit as incomplete.

## ADDED Requirements

### Requirement: An exit names its blockers and decisions

The exit SHALL name as a blocker a valid or unknown Lease, a held selection lock or proof slot, and a running process other than its own that refers to the runtime or hooks generations or to an installed runtime a selector names, and SHALL treat a process it cannot read as unknown. Without a record it SHALL ask, while a hooks path ETHOS owns remains, for the exact decision on that path.

#### Scenario: The exit's own process

- **WHEN** only the exit's own process refers to the repository's runtime
- **THEN** the exit preview names no running process as a blocker.

#### Scenario: A process cannot be read

- **WHEN** a running process's command line cannot be read
- **THEN** the exit preview names `adoption_exit_runtime_use_unknown` as a blocker.
