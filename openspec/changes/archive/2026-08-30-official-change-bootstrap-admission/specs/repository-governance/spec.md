## ADDED Requirements

### Requirement: Official Change bootstrap is a bounded write authority

An owned Work Lane with a valid current Lease SHALL be able to create and
complete exactly one official OpenSpec Change before its transient Commitment
exists. Bootstrap authority SHALL derive only from the official active Change
identifier and artifact graph, and SHALL cover only artifact paths under that
exact Change root.

#### Scenario: Official metadata starts the first Change

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no other active official Change exists
- **WHEN** the official OpenSpec command creates one valid Change metadata file
- **THEN** prewrite admits that Change's official proposal, specs, design, tasks, and metadata paths
- **AND** no product path, unrelated Change, archive path, or generated carrier is admitted

#### Scenario: Ordinary Commitment attribution replaces bootstrap

- **WHEN** the official Change becomes complete enough to compile its transient Commitment
- **THEN** current resolution uses ordinary Commitment and fresh-path attribution
- **AND** bootstrap authority grants no additional scope or durable permission

#### Scenario: Ambiguous or invalid bootstrap fails closed

- **WHEN** zero or several active Change identifiers are observed, an identifier is invalid, or a requested path is outside the official artifact graph
- **THEN** prewrite reports the first exact OpenSpec or uncovered-path gap
- **AND** historical archive authority, another Change, or a fallback path does not authorize the write
