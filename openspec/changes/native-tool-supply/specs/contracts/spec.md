## ADDED Requirements

### Requirement: Official requirement renames retain their semantic relation

The official OpenSpec compiler SHALL represent a valid RENAMED operation as an
acceptance relation binding its capability and exact source and destination names.
A rename-only Change SHALL not be misclassified as spec-free. Mixed rename and
requirement deltas SHALL preserve both meanings. Missing, empty or identical
endpoints SHALL fail without fabricating requirement text or a parallel carrier.

#### Scenario: Rename-only or mixed official intent

- **WHEN** the official projection contains a valid rename, alone or with modified requirements
- **THEN** acceptance binds the exact source and destination names
- **AND** changing either endpoint changes the compiled identity

#### Scenario: Incomplete or ambiguous rename

- **WHEN** an endpoint is missing, empty, non-textual or equal to its counterpart
- **THEN** compilation rejects the invalid relation instead of manufacturing acceptance
