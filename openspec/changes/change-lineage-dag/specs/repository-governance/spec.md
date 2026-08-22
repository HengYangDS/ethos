## ADDED Requirements

### Requirement: Change creation resolves lineage before effects

ETHOS SHALL resolve every declared predecessor digest to a valid immutable
Commitment carrier in the exact base Git tree before creating or moving a Work
Lane ref, materializing a worktree, or acquiring a Lease. The resulting lineage
graph SHALL be derived from Commitment and Git facts without a graph database,
successor back-links, or another semantic root.

#### Scenario: Fresh lane starts from historical predecessors

- **GIVEN** a fresh Change Commitment names one or more Commitment digests that
  resolve in the exact selected base tree
- **WHEN** `ethos lane start` evaluates dry-run or apply
- **THEN** both modes admit the same Commitment and predecessor set
- **AND** apply creates only the existing ref, worktree, carrier, and Lease
  effects

#### Scenario: A predecessor cannot be resolved

- **WHEN** any predecessor digest is malformed, absent, ambiguous, or does not
  identify a valid Commitment in the exact base tree
- **THEN** lane start fails before any ref, worktree, carrier, or Lease effect
- **AND** the result identifies the offending predecessor without falling back
  to mutable worktree or historical-state guesses

### Requirement: Change start recovery preserves exact lineage

In-lane Change rollover SHALL bind the complete canonical predecessor set into
its prepared request and successor Commitment identity. Recovery and
Attestation SHALL accept only the exact requested set, while requiring the old
Lease-bound Commitment digest to remain a member.

#### Scenario: Retry observes the exact successor lineage

- **WHEN** retry or recovery observes the exact successor Commitment, Git
  effect, Lease transition, and complete requested predecessor set
- **THEN** it recognizes or completes the original transition
- **AND** it emits an Attestation bound to that successor Commitment digest

#### Scenario: Predecessor set drifts across a retry

- **WHEN** a retry observes a successor with any predecessor added, removed, or
  substituted relative to the prepared request
- **THEN** recovery fails closed as request or effect identity mismatch
- **AND** it does not advance the Lease or emit a successful Attestation

### Requirement: Change lineage permits concurrency without global serialization

Governed Change lineage SHALL be a partial order. ETHOS SHALL serialize only
conflicting effects at their exact Git ref or scoped authority boundary and
SHALL NOT infer a repository-wide total order from predecessor edges.

#### Scenario: Independent successors proceed concurrently

- **GIVEN** two successor Commitments share a predecessor but have satisfied
  dependencies and disjoint scopes and effects
- **WHEN** they operate on distinct admitted refs or scopes
- **THEN** both may proceed without an artificial predecessor chain between
  them
- **AND** each later integration remains guarded by its own exact-CAS boundary
