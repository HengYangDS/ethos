## ADDED Requirements

### Requirement: A Change cites the decision records that name it

A decision record that names an active Change in inline code SHALL be cited by that Change before
it archives: one of the Change's artifacts SHALL contain the record's `DR-####` identity as a word
or its file name. Archive readiness SHALL otherwise report
`openspec_decision_uncited:<change>:<identity>`, which blocks the archive preview and the proof
that selects the Change. Archive readiness SHALL read the records from the exact tree it judges.

#### Scenario: A record names an uncited Change

- **WHEN** a decision record names an active Change in inline code and no artifact of the Change
  contains the record's identity or file name
- **THEN** archive readiness reports `openspec_decision_uncited` with the Change and the identity
- **AND** the archive preview and the proof of that Change block

#### Scenario: The Change cites the record

- **WHEN** an artifact of the Change contains the record's identity or file name
- **THEN** the record does not block the Change's archive

#### Scenario: A record mentions the Change only in prose

- **WHEN** a decision record mentions a Change's name only outside inline code
- **THEN** the record does not name the Change and does not block its archive
