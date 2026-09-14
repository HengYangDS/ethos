## REMOVED Requirements

### Requirement: OpenSpec active carrier residue is visible across protected branch trees

**Reason**: Active intent is not residue. The former requirement conflates source
acceptance with completed delivery and creates an archive-before-integration cycle.

**Migration**: Replace its role-specific prohibitions with the active-intent
observation and exact source-proof requirements below.

## ADDED Requirements

### Requirement: OpenSpec active intent is visible across governed branch trees

ETHOS SHALL observe active official Changes in configured integration, accepted
and release Git trees. Active intent SHALL remain valid through source
integration and delivery. Each transition SHALL separately require exact source
and policy proof, current authority and its own CAS preconditions.

#### Scenario: active intent accompanies accepted source

- **WHEN** an accepted or release source tree contains a valid active Change
- **THEN** its presence is an ordinary observation, not an archive-required gap
- **AND** current source proof and effect admission remain required.

#### Scenario: another governed branch carries active intent

- **WHEN** the current checkout differs from a configured governed branch
- **THEN** its observed Change names remain visible with the exact branch role
- **AND** presence alone is neither a warning nor authority to mutate that branch.

#### Scenario: a required Git observation is unavailable

- **WHEN** ETHOS cannot read a required branch or source tree
- **THEN** the report preserves UNKNOWN and its precise missing fact
- **AND** it does not silently interpret failure as an empty Change list.

### Requirement: Repository transition proof binds source intent independently of archive

ETHOS SHALL admit repository-transition proof only for the exact source commit,
tree, official acceptance and required policy floor. Active and attested archived
intent SHALL use the same source-binding rule. Authoring Lease lifetime SHALL
not replace current effect authority or invalidate accepted source evidence.

#### Scenario: exact source carries unfinished delivery intent

- **WHEN** exact proof covers a valid active Change and the declared source floor
- **THEN** candidate-to-accepted admission may consume that proof before archive
- **AND** it does not assert completed delivery or authorize a later effect.

#### Scenario: carried acceptance differs from source

- **WHEN** proof names the correct commit but carries different acceptance
- **THEN** repository-transition admission rejects the intent binding
- **AND** green check results cannot compensate for that mismatch.

#### Scenario: the authoring Lease has retired

- **WHEN** source proof remains exact and applicable after its Work Lane retires
- **THEN** an independently authorized repository transition can consume it
- **AND** current-lane authoring still requires its own live Lease.
