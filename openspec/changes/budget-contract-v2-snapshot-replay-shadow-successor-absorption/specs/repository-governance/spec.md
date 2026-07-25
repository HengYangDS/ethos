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

#### Scenario: detached dirty residue is normalized without changing bytes

- **GIVEN** one registered detached historical worktree has an absent Work Lane
  ref, no valid owner, a committed HEAD already in accepted history, and dirty
  tracked or untracked bytes
- **WHEN** a maintainer prepares it for target-specific behavioral resolution
- **THEN** the detached observation, reflog, HEAD, index, dirty inventory,
  content digests, session ownership, and path occupancy SHALL be captured first
- **AND** any reconstructed historical Work Lane ref SHALL point to the exact
  detached HEAD and SHALL NOT change index or working bytes
- **AND** ref reconstruction SHALL NOT mint ownership or effect authority
- **AND** an accepted target-specific Chronicle SHALL distinguish behavioral
  absorption, rejected historical behavior, preservation, retirement, and later
  package clearing before any destructive effect.

#### Scenario: expired dirty successor is semantically absorbed before closeout

- **GIVEN** a linked Work Lane has an expired or missing lease, no valid Claim,
  no process or open-file user, and dirty tracked or untracked bytes
- **AND** an accepted target-specific Chronicle binds its exact head, merge
  base, worktree registration, dirty paths, patch digest, and ownerless state
- **WHEN** current accepted source and tests prove every useful hunk exact or
  stronger, while rejected historical behavior is named explicitly
- **THEN** semantic absorption SHALL be distinct from byte preservation
- **AND** historical product code SHALL NOT be replayed merely to clean the lane
- **AND** native preserve-retire SHALL re-observe the complete source before
  preserving its exact bytes and removing only the named branch and worktree
- **AND** any newly valid owner, source drift, Chronicle drift, process
  occupancy, preservation failure, or accepted-basis drift SHALL block the
  effect
- **AND** recovery-package clear SHALL remain blocked until a separate accepted
  exact-manifest decision proves no unique behavior remains.

#### Scenario: overlapping valid-owner lanes remain protected

- **GIVEN** valid-owner foreign lanes overlap source or test paths mentioned by
  the ownerless semantic judgment
- **WHEN** the ownerless authority carrier is authored, proved, landed, or
  applied
- **THEN** visibility and overlap SHALL NOT authorize writes, tests, land,
  retirement, cleanup, or ownership transfer for those foreign lanes
- **AND** the effect SHALL be limited to the exact ownerless source named by the
  accepted Chronicle.
