## ADDED Requirements

### Requirement: One executor owns each local repository ref effect

Every governed local ref mutation SHALL be executed by one TransitionPlan-bound
repository-effect owner that performs effect-time re-observation, exact CAS,
post-observation, Attestation persistence, and bounded compensation or recovery.

#### Scenario: A local ref effect succeeds

- **WHEN** an admitted plan's exact preconditions still match
- **THEN** the executor applies the declared CAS
- **AND** the post-observation and effect Attestation bind the same plan digest

#### Scenario: A lifecycle command requests a ref effect

- **WHEN** start, land, accepted closeout, rebind, refresh, handoff, or retirement needs a local ref mutation
- **THEN** it compiles its semantic authority into the common executor
- **AND** it does not own a parallel ref recovery state machine

### Requirement: Hooks never own Lease transition effects

The reference-transaction hook SHALL validate exact intent and observe Git ref
outcomes without advancing, revoking, or replacing Lease authority.

#### Scenario: An ordinary owned Work Lane commit moves its ref

- **WHEN** Git commits the branch ref after pre-commit authoring admission
- **THEN** the hook does not rewrite Lease state
- **AND** subsequent authority reads bind the stable Lease/Commitment generation to fresh branch HEAD and tree Facts

### Requirement: Rejected raw Git transitions fail cleanly or explicitly

The hook SHALL compensate an already projected index/worktree only from an
exactly proven target projection and SHALL never guess across an unrelated
overlay.

#### Scenario: A clean protected checkout is projected before rejection

- **WHEN** Git leaves HEAD unchanged and index/worktree exactly equal the rejected target tree
- **THEN** the hook restores the exact current HEAD tree and verifies the restoration

#### Scenario: The index or worktree contains another overlay

- **WHEN** exact projection ownership cannot be proven
- **THEN** compensation is refused
- **AND** no unrelated staged or unstaged content is silently discarded
