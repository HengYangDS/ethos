## ADDED Requirements

### Requirement: Authorized Work Lane cohort closeout is exact and evidence-bound

ETHOS SHALL treat a user-authorized Work Lane cohort closeout as an owned
governance operation over individually observed targets, not as reusable
authority over every visible foreign lane.  Before an exceptional handoff,
preservation, semantic replay, supersession, or retirement effect, the owned
carrier SHALL bind the target branch, current head, relation to accepted truth,
lease/incarnation observation, claim binding, dirty provenance, intended
disposition, recovery plan, and evidence reference.  A target fact change
SHALL invalidate the pending effect until a new observation and decision are
recorded.

#### Scenario: A visible foreign lane is not wildcard authority

- **WHEN** an owned carrier audits a visible foreign Work Lane
- **THEN** it records an exact target observation and allows only the native
  holder-bound or accepted exceptional lifecycle path for that target
- **AND** it does not allow a batch, wildcard, or stale observation to write,
  land, retire, or delete a different foreign Work Lane.

#### Scenario: A moving target invalidates its decision

- **WHEN** a target's head, dirty state, holder, lease generation, or relation
  to accepted truth changes after a decision was prepared
- **THEN** ETHOS blocks the planned apply effect for that decision
- **AND** the owned carrier re-observes the target before producing a new
  decision.

### Requirement: Dirty and unbound Work Lane content is preserved before destructive closeout

ETHOS SHALL preserve a dirty foreign Work Lane or diverged unbound Work Lane
reference before an irreversible closeout action.  The preservation outcome
SHALL record Git status provenance, exact target head, recoverable content
manifest or patch digest, semantic comparison result, and the resulting
disposition.  A clean accepted-absorption finding alone SHALL NOT discard an
unpreserved dirty overlay.

#### Scenario: Dirty foreign lane requires preservation first

- **WHEN** a full lane observation reports a foreign Work Lane with tracked,
  deleted, conflicted, or untracked content
- **THEN** the closeout carrier creates or retains a verifiable preservation
  package before requesting retirement
- **AND** the lane remains preserve-replay or blocked until its unique semantic
  delta is accepted or intentionally superseded.

#### Scenario: Diverged unbound ref remains recoverable

- **WHEN** an unbound Work Lane ref diverges from accepted truth
- **THEN** ETHOS requires a recoverable semantic or preservation outcome before
  its native unbound retirement path
- **AND** it does not delete the ref merely because it lacks a linked worktree.
