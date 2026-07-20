## ADDED Requirements

### Requirement: Real history-residue effects use a distinct local closeout successor

The system SHALL keep the dated tracked-work archive immutable and SHALL bind any
later real local-state maintenance to a distinct successor claim and exact
external receipt.

#### Scenario: Historical operator apply is admitted without rewriting the predecessor

- **WHEN** a verified maintenance receipt postdates an archive that excluded real effects
- **THEN** a new successor records the receipt HEAD, inventory digest, artifact digests, deletion counts, and source postconditions
- **AND** the predecessor archive remains byte-for-byte unchanged
- **AND** the record does not infer current ignored-state counts from historical apply counts

#### Scenario: Local closeout preserves authority boundaries

- **WHEN** the successor completes its archive and promotion transitions
- **THEN** accepted closeout uses `maintainer_break_glass_local`
- **AND** remote publication and hosted execution remain deferred and unclaimed
- **AND** r7 plus foreign and unbound lanes remain observe-only
- **AND** only the current owned lane is eligible for retirement

#### Scenario: Control replacement requires external verification

- **WHEN** the final candidate differs on configured control paths
- **THEN** accepted closeout requires an external control-replacement receipt outside the candidate tree
- **AND** the receipt binds exact accepted and candidate heads, control paths, both control digests, verifier digest, and executed-proof digest
