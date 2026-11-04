## MODIFIED Requirements

### Requirement: A repository exit is previewed before any effect

`ethos adopt --exit` SHALL report, without any effect, the configuration it would restore, the selectors it would remove with their hashes, each linked worktree's hooks path, the Lease snapshot, the unlanded topic branches and a plan digest over them. It SHALL name a valid or unknown Lease, a held selection lock or proof slot, or a running process that uses the runtime as a blocker, and SHALL ask the user rather than guess while no record exists and a hooks path ETHOS owns remains.

#### Scenario: An exit is inspected

- **WHEN** `ethos adopt --exit --json` runs in an adopted repository with a recorded configuration
- **THEN** it reports the restoration, the selector hashes and a plan digest
- **AND** no file, configuration or selector changes.

#### Scenario: No configuration was recorded

- **WHEN** the repository was adopted before installation recorded its configuration
- **AND** its hooks path is still ETHOS's
- **THEN** the exit preview requires the user's choice instead of unsetting the hooks path.

#### Scenario: A lane holds a live Lease

- **WHEN** a Work Lane of the repository holds a valid Lease
- **THEN** the exit preview names that Lease as a blocker
- **AND** its plan digest differs from one made before the Lease.

#### Scenario: A running process uses the runtime

- **WHEN** a running process refers to the repository's runtime or hooks generations
- **THEN** the exit preview names `adoption_exit_runtime_in_use` as a blocker.

#### Scenario: A repository is not adopted

- **WHEN** the repository has no runtime selector and no hooks path that ETHOS owns
- **THEN** the exit reports `adoption_exit_not_adopted` and plans no effect
- **AND** it reads no hand-made file as a record.

## ADDED Requirements

### Requirement: A previewed exit is applied in a fenced order

With `--apply`, `--authorize`, the current head and the previewed plan digest, `ethos adopt --exit` SHALL, under the runtime selection lock, write a receipt, restore the recorded configuration, verify that no worktree's hooks path is still ETHOS's, and only then remove the selectors and the record. A failure SHALL restore the prior configuration, selectors and record exactly, and the exit SHALL NOT change consumer records.

#### Scenario: An adopted repository exits

- **GIVEN** a repository with its own hooks path that adopted ETHOS
- **WHEN** the exit is applied with the previewed digest
- **THEN** the hooks path is its own again and no selector remains
- **AND** the receipt holds the selector hashes and the configuration before and after.

#### Scenario: The plan changed after the preview

- **WHEN** the apply names a digest that differs from the current plan
- **THEN** the exit is refused and nothing changes.

#### Scenario: An exit fails after restoring the configuration

- **WHEN** removing a selector fails
- **THEN** the configuration, the selectors and the record are those before the exit.

### Requirement: Status reports an exit

After an exit, status SHALL report the exit and its receipt as a fact, and a repository without a repository profile SHALL NOT require hooks once it has exited.

#### Scenario: Status after an exit

- **WHEN** status runs in a repository that exited
- **THEN** it reports the exit and its receipt.
