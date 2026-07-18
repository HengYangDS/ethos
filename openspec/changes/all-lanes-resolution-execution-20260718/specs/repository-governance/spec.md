## MODIFIED Requirements

### Requirement: Preservation-bound exceptional Work Lane retirement

ETHOS SHALL offer an explicit `preserve-retire` exceptional disposition for a
dirty foreign or orphan Work Lane only after accepted Chronicle evidence has
bound the exact resolution.

#### Scenario: dirty residual lane is preserved without retirement

- **GIVEN** a linked Work Lane is dirty, missing a normalized lease, and its
  accepted Chronicle decision selects `lane_resolution/preserve`
- **WHEN** a maintainer records and applies the exact native two-phase decision
- **THEN** ETHOS recomputes the lane observation
- **AND** writes and verifies a digest-bound bundle, tracked patch, untracked
  archive when needed, and manifest
- **AND** retains the exact branch and linked worktree for later semantic replay
- **AND** emits a non-authoritative preservation receipt

#### Scenario: dirty lane is preserved before retirement

- **GIVEN** a linked Work Lane is dirty and its accepted Chronicle decision
  selects `lane_resolution/preserve-retire`
- **WHEN** a maintainer records a break-glass decision and applies it with an
  irreversible confirmation
- **THEN** ETHOS recomputes the exact lane observation
- **AND** writes a digest-bound bundle, tracked patch, untracked archive when
  needed, and manifest before removing the exact branch and linked worktree
- **AND** rejects the retirement if preservation is incomplete or stale
- **AND** emits a non-authoritative completion receipt with reconciliation
  required

#### Scenario: ordinary dirty retirement remains blocked

- **WHEN** a dirty Work Lane is resolved with plain `retire`
- **THEN** ETHOS reports `dirty_lane_retirement_blocked`
- **AND** it does not remove the branch or worktree

#### Scenario: Chronicle disposition is bound before the effect

- **GIVEN** an accepted Chronicle explicitly selects
  `lane_resolution/preserve`, `lane_resolution/retire`,
  `lane_resolution/preserve-retire`, or `lane_resolution/block` for one
  resolution class
- **WHEN** a maintainer records a native two-phase resolution decision
- **THEN** ETHOS binds the Chronicle path and SHA-256 digest together with the
  exact target observation digest
- **AND** native apply recomputes that observation before any effect
- **AND** a changed target blocks the decision rather than inheriting the prior
  disposition.
