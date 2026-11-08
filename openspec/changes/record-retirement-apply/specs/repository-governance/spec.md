## MODIFIED Requirements

### Requirement: Store records retire only through an allowlisted write-ahead plan

ETHOS SHALL retire Git-common store records only through `ethos hook retire-records`, run by the
runtime that `runtime/CURRENT` selects. Its preview SHALL plan only allowlisted kinds older than
their floor that no live member, kept record, decoded carrier or accepted tree names. Its apply
SHALL delete only planned items that a fresh scan still selects, through recoverable tombstones,
while no other ETHOS interpreter of the repository runs. Any other store file SHALL be kept.

#### Scenario: An encoded mention keeps an item

- **WHEN** a kept store file names an artifact's digest inside zip, gzip, tar or base64 content
- **THEN** the preview keeps the artifact and every item that the artifact names in turn

#### Scenario: A kept carrier cannot be decoded

- **WHEN** a kept store file exceeds the declared decode depth or bytes, or its archive is damaged
- **THEN** the preview refuses with `record_retirement_carrier_undecodable` and names the file

#### Scenario: A foreign producer writes under an owned name

- **WHEN** a file in an owned directory matches no allowlisted writer's schema
- **THEN** the preview reports it by path and bytes and keeps it

#### Scenario: Another runtime runs the verb

- **WHEN** the invoking interpreter or build is not the one that `runtime/CURRENT` selects
- **THEN** the preview refuses with `record_retirement_runtime_unselected` and writes nothing

#### Scenario: The accepted floor cannot be read

- **WHEN** the accepted branch is absent or its binding's rules blob does not parse
- **THEN** the preview refuses with `record_retirement_floor_unreadable` and writes nothing

#### Scenario: A proof holds the slot

- **WHEN** a proof holds the repository's proof slot
- **THEN** the preview refuses with `record_retirement_proof_slot_held` and writes nothing

#### Scenario: Young items and plan contents

- **WHEN** an unnamed item's newest file is younger than its floor, grace for artifacts and record
  for lane retirement units
- **THEN** the item is kept
- **AND** the plan names the accepted commit behind the floors, the frozen cutoffs and each
  candidate's kind, path, size, mtime and state

#### Scenario: A writer adopts an existing record

- **WHEN** a writer writes content identical to an existing content-addressed file
- **THEN** the file's mtime is refreshed, so its floor starts again

#### Scenario: An interrupted apply continues

- **WHEN** an apply stopped after renaming items to tombstones or deleting part of a lane unit
- **THEN** the next preview or apply restores every tombstone first, and a rerun of the plan deletes
  the rest of the unit, its receipt last

#### Scenario: A swap during the compare keeps what it names

- **WHEN** an Attestation set swap or an accepted-branch advance names a tombstoned item before the
  unlink
- **THEN** the item is restored and kept

#### Scenario: Another ETHOS interpreter of the repository runs

- **WHEN** a process runs an ETHOS interpreter of another runtime generation, of an installation
  this repository uses or of one of its worktrees, or the process listing cannot be read
- **THEN** the batch defers with `record_retirement_batch_deferred:<kind>:writer` and is restored
- **AND** a process of another repository or a hook run does not defer it

#### Scenario: A receipt binds each run

- **WHEN** an apply run ends
- **THEN** its receipt records per kind what it deleted, found absent, kept and deferred, with
  reasons, and that no deleted digest is among the live members' tokens
- **AND** an apply of a plan whose receipt has no deferral deletes nothing and reports
  `already_applied`

#### Scenario: A writer adopts a record during an apply

- **WHEN** a writer writes content identical to a record that the apply renamed away
- **THEN** the writer links the record again and does not fail with a collision

#### Scenario: An apply is refused

- **WHEN** the plan is missing, altered or of schema 1, `--authorize` is absent or another apply or
  preview holds `retention.lock`
- **THEN** the apply refuses with its gap and deletes nothing
