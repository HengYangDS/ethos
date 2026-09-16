## ADDED Requirements

### Requirement: Lane intent respects its native contribution boundary

ETHOS SHALL resolve a Work Lane's current official intent within its native
creation and contribution history. A merge inherited before lane creation SHALL
NOT displace a different active Change. Existing effect records provide that
boundary without extending Lease or introducing another intent carrier.

#### Scenario: New lane inherits an archived predecessor and active work

- **WHEN** an accepted tree contains an archived predecessor and a different
  active Change, and a new owned lane starts at that tree
- **THEN** prewrite and default planning select the active Change
- **AND** the predecessor archive does not authorize or block the active files

#### Scenario: Same lane archives its own contribution

- **WHEN** a lane merges incoming active intent and then archives its own Change
- **THEN** its closeout retains the archived contribution's identity
- **AND** it does not silently take ownership of the incoming Change

#### Scenario: An explicit selection is carried through proof

- **WHEN** plan or prove explicitly selects a present official Change
- **THEN** its accepted intent, execution plan and proof carry that same identity
- **AND** new proof binds the current lane and Lease generation
- **AND** an archived predecessor's proof cannot substitute for that selection

#### Scenario: Contribution provenance is ambiguous or corrupt

- **WHEN** competing creation or contribution facts cannot establish the selected
  lane boundary, or selected effect evidence is invalid
- **THEN** the observation reports a precise unresolved provenance gap
- **AND** it does not guess from task counts or unrelated archived intent
