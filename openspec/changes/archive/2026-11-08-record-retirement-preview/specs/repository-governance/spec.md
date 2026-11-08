## ADDED Requirements

### Requirement: Store records retire only through an allowlisted write-ahead plan

ETHOS SHALL retire Git-common store records only through `ethos hook retire-records`, run by the
runtime that `runtime/CURRENT` selects. Its preview SHALL classify only allowlisted kinds by their
writers' schemas, keep every item that a live member, a kept record, a decoded carrier or the
accepted tree names, select only items older than their floor, and write its plan before any
deletion. Any other store file SHALL be reported and kept.

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
