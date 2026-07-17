## ADDED Requirements

### Requirement: Report distinguishes local publication and hosted observation state

ETHOS report SHALL expose local publication readiness and hosted provider
observation status as separate read-only projections without performing a
remote probe or minting proof, hosted-success, or publication authority.

#### Scenario: Current hosted observation is projected

- **WHEN** ethos report runs and the configured hosted observation artifact
  binds the current tracked head
- **THEN** report data SHALL include hosted_observation state, freshness,
  provider-state summary, and bounded observation gaps
- **AND** those gaps SHALL remain advisory rather than repository proof
  required_gaps
- **AND** hosted GitHub status claimed, hosted GitLab status claimed, and remote
  publication claimed SHALL remain false

#### Scenario: Hosted observation is missing invalid or stale

- **WHEN** the hosted observation artifact is missing, malformed, or bound to a
  different tracked head
- **THEN** report SHALL expose missing, invalid, or stale hosted observation
  state
- **AND** it SHALL provide a bounded next action to rerun the observation owner
  script
- **AND** the scorecard SHALL remain read-only

#### Scenario: Local publication readiness is projected

- **WHEN** ethos report summarizes current blockers and proof readiness
- **THEN** report data SHALL include a local_publication projection that
  distinguishes ready from blocked local state
- **AND** the projection SHALL list its local blockers
- **AND** remote publication claimed SHALL remain false
- **AND** the projection SHALL NOT replace the ethos publish transition verdict
