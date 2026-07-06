## ADDED Requirements

### Requirement: Foreign Work Lane Collaboration Read Model

ETHOS SHALL expose foreign Work Lanes as observable, current-actor observe-only
subjects unless an owner, accepted handoff, or maintainer break-glass path admits
mutation.

#### Scenario: foreign lane capability is observe-only

- **GIVEN** a repository has a linked foreign `work/*` worktree
- **WHEN** `ethos status --json` reports the lane in `data.foreign_work_lanes`
- **THEN** the lane item exposes `current_actor_capability=observe`
- **AND** `allowed_actions` contains only `observe`
- **AND** `forbidden_actions` includes `write`, `land`, and `retire`
- **AND** the write policy is owner-only
- **AND** the retire policy requires the owner, accepted handoff, or maintainer
  break-glass evidence
