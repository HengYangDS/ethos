# Adapters Delta

## MODIFIED Requirements

### Requirement: Work Lane Topology
ETHOS SHALL classify linked worktrees by local repository role and SHALL keep remote review refs outside local authoring authority.

#### Scenario: Role policy is projected
- **WHEN** `ethos status --json` or `ethos lane status --json` reports workspace topology
- **THEN** local role order is `release_root -> accepted_root -> candidate -> work_lane`
- **AND** a configured `proposal/*` target is classified only by publication admission as `proposal_ref`
- **AND** no proposal ref grants local authoring or Lease authority.

#### Scenario: Foreign Work Lanes exist
- **WHEN** `ethos status` or `ethos lane status` inspects a repository with a
  linked `work/*` lane outside the current checkout
- **THEN** ETHOS reports the foreign lane path, branch, head, and role from Git
  worktree metadata
- **AND** ETHOS reports `foreign_work_lane_present` as a coordination signal
- **AND** ETHOS does not read, modify, close, or clean the foreign lane
- **AND** ETHOS reports a non-authoritative action preview with observe as the
  only candidate action and write, land, and retire blocked
- **AND** actual mutation re-evaluates its exact current request.

### Requirement: Prewrite Admission
ETHOS SHALL admit tracked authoring only from an owned `work/*` lane.

#### Scenario: Protected root write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from an accepted
  root, candidate, detached checkout, or other non-Work-Lane checkout
- **THEN** ETHOS blocks the request with `protected_lane_prewrite_blocked`.

#### Scenario: Owned Work Lane write is requested
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane whose editor root matches the checkout root
- **THEN** ETHOS admits the write and returns a structured admission report.

#### Scenario: Work Lane write lacks editor-root binding
- **WHEN** `ethos lane prewrite` checks tracked candidate paths from a `work/*`
  lane without editor-root binding
- **THEN** ETHOS blocks the request with `editor_root_missing`.

#### Scenario: Proposal ref is checked out locally
- **WHEN** `ethos lane prewrite` evaluates tracked mutation from a `proposal/*` checkout
- **THEN** the checkout has no authoring role
- **AND** ETHOS blocks the write rather than suggesting that the proposal ref is a Work Lane.
