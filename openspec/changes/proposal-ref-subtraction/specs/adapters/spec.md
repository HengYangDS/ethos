# Adapters Delta

## MODIFIED Requirements

### Requirement: Work Lane Topology
ETHOS SHALL classify linked worktrees by local repository role and SHALL keep remote review refs outside local authoring authority.

#### Scenario: Role policy is projected
- **WHEN** `ethos status --json` or `ethos lane status --json` reports workspace topology
- **THEN** local role order is `release_root -> accepted_root -> candidate -> work_lane`
- **AND** a configured `proposal/*` target is classified only by publication admission as `proposal_ref`
- **AND** no proposal ref grants local authoring or Lease authority.

### Requirement: Prewrite Admission
ETHOS SHALL admit tracked authoring only from an owned `work/*` lane.

#### Scenario: Proposal ref is checked out locally
- **WHEN** `ethos lane prewrite` evaluates tracked mutation from a `proposal/*` checkout
- **THEN** the checkout has no authoring role
- **AND** ETHOS blocks the write rather than suggesting that the proposal ref is a Work Lane.
