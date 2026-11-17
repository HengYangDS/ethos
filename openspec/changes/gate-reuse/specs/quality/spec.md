## ADDED Requirements

### Requirement: Gate results carry an input key before any result is reused

Each gate of an executed exact-source proof run SHALL carry an input key: a digest of its identity,
the committed paths its statement selects and its named inputs. The run SHALL record each key with
its verdict, SHALL still execute a gate whose key an earlier result carries, SHALL record and
count the comparison of the two verdicts, and SHALL report a differing one as a note. No gate
SHALL be skipped for an earlier result.

#### Scenario: A gate's key repeats

- **WHEN** an executed proof run reaches a gate whose input key an earlier recorded result carries
- **THEN** the gate executes, and the run's record names the comparison of the two verdicts
- **AND** the comparison says whether the earlier result was of another tree
- **AND** the command's result counts the comparison by its state

#### Scenario: Two decided results of one key differ

- **WHEN** a gate passes and an earlier result of the same key blocked, or the reverse
- **THEN** the result carries a note that names the gate, the key and the earlier result's tree
- **AND** the proof's verdict, required gaps, artifact and Attestation are those of a run without
  any record

#### Scenario: A gate has no statement of its inputs

- **WHEN** a gate runs a declared command, or a provider that the product's table does not name
- **THEN** its key covers every committed path

#### Scenario: A gate reads outside the committed tree

- **WHEN** a gate's provider reads references, history, local Git configuration, ignored files, a
  prepared environment, a built artifact or the network
- **THEN** its key is recorded as open
- **AND** its comparisons are counted as open in the result

#### Scenario: A provider opens a file outside its statement

- **WHEN** the process of a provider with a statement opens a committed file that its statement
  does not select
- **THEN** the record names the gate and the file
- **AND** the gate's verdict is unchanged

#### Scenario: A prerequisite held a gate

- **WHEN** a gate did not execute because a prerequisite did not pass
- **THEN** no key and no verdict of that gate is recorded

#### Scenario: The Git directory holds local attribute lines

- **WHEN** the Git directory's local attributes file holds lines that are not blank and not a
  comment
- **THEN** the result and the record carry their count
- **AND** neither carries a pattern of that file

#### Scenario: The source changed while the gates ran

- **WHEN** the execution source no longer equals the commit after the gates
- **THEN** no key and no verdict of that run is recorded

#### Scenario: The record cannot be read or written

- **WHEN** the record store is missing, unreadable or refuses a write
- **THEN** the proof's verdict is unchanged and the result names the record as unavailable
- **AND** a record that cannot be parsed holds no earlier result
