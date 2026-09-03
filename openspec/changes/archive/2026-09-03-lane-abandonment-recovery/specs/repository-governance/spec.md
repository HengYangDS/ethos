## ADDED Requirements

### Requirement: Destructive Work Lane retirement is a resumable observed transition

ETHOS SHALL execute authorized destructive Work Lane retirement as one
receipt-bound transition over the exact worktree, branch ref, and Lease
carriers. Before the first effect it MUST persist the immutable request and
verify a surviving repository control root, the Git executable, every process
working directory, the target ref and HEAD, worktree cleanliness, Lease state,
and caller authority. After every attempted effect it MUST re-observe native
carrier state and derive `completed_effects` and `remaining_effects` from those
facts rather than from process-local flags. Lease revocation MUST occur only
after the worktree and ref are absent.

#### Scenario: Execution coordinates fail before destruction

- **WHEN** Git cannot be resolved or the surviving control root and effect
  working directories cannot be used before an authorized retirement
- **THEN** ETHOS blocks before removing the worktree, branch ref, or Lease
- **AND** the structured result identifies the failed preflight coordinate.

#### Scenario: Failure follows worktree removal

- **WHEN** the exact worktree is removed and a later ref effect cannot start or
  complete
- **THEN** ETHOS reports `state=partial_transition`
- **AND** the durable progress receipt reports worktree removal as complete and
  ref deletion and Lease revocation as remaining
- **AND** no later process is launched from the removed worktree.

#### Scenario: Recovery converges from native carrier facts

- **WHEN** an authorized caller supplies an exact current retirement receipt
  after a partial effect
- **THEN** ETHOS re-observes the surviving control root, ref, worktree, and Lease
- **AND** it applies only the effects still required for the declared terminal
  state
- **AND** a repeated recovery of the same terminal request is recognized as
  complete without a second destructive effect.

#### Scenario: Recovery authority or coordinates are ambiguous

- **WHEN** the request bytes, repository identity, target HEAD, accepted
  authority, or caller authority differ from the receipt, or a valid Lease is
  held by another actor
- **THEN** ETHOS fails closed without changing any carrier
- **AND** it does not reinterpret an old receipt or mint replacement authority.

### Requirement: Abandonment uses the sole retirement transition owner

ETHOS SHALL expose explicit abandonment of a clean divergent Work Lane through
the same retirement request, observation, reducer, effect executor, and progress
receipt used by linked retirement. The repository SHALL retain no independent
abandonment mutation engine or compatibility reader for retired receipt
schemas.

#### Scenario: Owner-authorized clean divergent lane is abandoned

- **WHEN** the exact holder authorizes abandonment of its clean divergent
  `work/*` Lane with a valid Lease and a structured reason
- **THEN** ETHOS derives an immutable request and may converge the worktree, ref,
  and Lease to absence through exact effects
- **AND** the terminal receipt binds the reason, authority, original HEAD and
  tree, completed effects, and terminal observations.

#### Scenario: Active foreign ownership remains protected

- **WHEN** a clean divergent Lane has a valid Lease whose holder is not the
  invoking actor
- **THEN** abandonment and recovery both block before effects
- **AND** explicit authorization flags or receipt possession do not substitute
  for holder authority.
