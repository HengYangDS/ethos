## MODIFIED Requirements

### Requirement: Work Lane Lifecycle Resolution

ETHOS SHALL keep routine mechanically determined lane lifecycle local and SHALL
record only exceptional interpretive judgments as evidence-bound Chronicle
`decision` events. Chronicle SHALL NOT become lease telemetry or a separate lane
resolution database.

#### Scenario: routine lifecycle remains local

- **WHEN** a lease is acquired, renewed, resumed, locally handed off, expires, or
  the same holder retires a clean mechanically proven landed lane
- **THEN** ETHOS uses ignored local coordination and postcondition receipts
- **AND** no tracked Chronicle decision is required.

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** orphan recovery, foreign retirement, non-mechanical supersession,
  disputed handoff, preserve, block, or irreversible deletion is requested
- **THEN** a separate owned governance Work Lane has already promoted a
  Chronicle decision binding policy, evidence, exact head, lane-incarnation
  digest, disposition, recovery plan, and target-observation digest
- **AND** cleanup recomputes the mutable target facts before its first
  destructive step
- **AND** any mismatch blocks cleanup and requires a new decision
- **AND** the decision authorizes an effect while postconditions alone prove what
  was actually removed.

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** lane ownership, lease state, tracked/untracked contents, or recovery
  status is dirty, missing, ambiguous, or unknown
- **THEN** ETHOS preserves or blocks the lane instead of automatically deleting
  it
- **AND** irreversible deletion requires an accepted decision proving the exact
  target and why preservation is impossible or no longer required.

#### Scenario: break-glass reconciles after emergency action

- **GIVEN** a predeclared break-glass Commitment binds verified maintainer
  identity, exact target/head, reason, blast radius, expiry, preservation
  default, and postcondition plan
- **WHEN** an emergency command independently verifies those facts and acts
  before a new Chronicle decision can be promoted
- **THEN** it emits a digest-bound receipt and blocks later integration and
  publication
- **AND** a separate governance Work Lane promotes post-hoc judgment and
  reconciles residue before the block clears
- **AND** a self-supplied flag or holder string is insufficient.

#### Scenario: lane handoff is recorded as Chronicle resolution

- **GIVEN** a Work Lane handoff cannot be resolved by the normal local
  offer/accept protocol or becomes disputed
- **WHEN** an accepted exceptional judgment resolves the handoff
- **THEN** ETHOS records a Chronicle `decision` event binding the prior and next
  holder observations, evidence, exact head, lane-incarnation digest, and result
- **AND** routine local handoff remains ignored coordination and does not require
  tracked Chronicle telemetry
- **AND** the decision does not replace the active destination-local Lane Lease.

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **GIVEN** a Work Lane has missing, stale, ambiguous, or legacy holder evidence
- **WHEN** ETHOS audits the lane for exceptional closeout or cleanup
- **THEN** orphan-like facts remain observations requiring a separate accepted
  resolution decision before destructive action
- **AND** the durable outcome records `retire`, `preserve`, `block`, `handoff`, or
  `break_glass` together with exact target and recovery evidence
- **AND** dirty or owner-unknown lanes are preserved or blocked rather than
  automatically deleted.

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **GIVEN** one clean ownerless source Work Lane has diverged because its
  historical evidence and carrier bytes differ from an independently accepted
  current-baseline implementation of its useful behavior
- **AND** a target-specific accepted Claim and Chronicle bind its exact ref,
  exact source head, semantic basis, recovery plan, and `lane_resolution/retire`
  policy
- **WHEN** the native resolver records and applies a fresh decision for that
  exact linked source with break-glass and irreversible confirmation
- **THEN** it SHALL re-observe the source before effect and emit a receipt after
  the exact retirement
- **AND** tree inequality, a missing lease, a preservation package, or an
  inventory entry alone SHALL NOT authorize retirement
- **AND** the authority SHALL NOT extend to another lane, a valid lease, remote
  mutation, or a hosted-provider claim.

#### Scenario: dirty ownerless source retires only after semantic absorption and preservation

- **GIVEN** one named linked Work Lane is dirty, has no active lease, and its
  committed head is an ancestor of the current accepted branch
- **AND** an accepted target-specific Claim and Chronicle bind its exact ref,
  exact source head, current semantic absorption basis, remaining dirty-path
  recovery plan, and `lane_resolution/preserve-retire` policy
- **WHEN** the native resolver records and applies a fresh decision with
  break-glass and irreversible confirmation after the absorption carrier's own
  local proof, candidate land, and accepted closeout
- **THEN** it SHALL re-observe and preserve the exact source contents before
  removing only that source branch and worktree, then write a receipt
- **AND** a missing lease, accepted ancestry, prior package, or historical source
  diff alone SHALL NOT authorize retirement of another lane, candidate movement,
  remote mutation, or a hosted-provider claim.
