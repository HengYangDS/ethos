## Purpose
Define the single Git-native transaction boundary that compiles official OpenSpec intent and fresh repository facts into exact compare-and-swap effects and durable Attestations.

## ADDED Requirements

### Requirement: Official OpenSpec is the sole tracked intent carrier

ETHOS SHALL compile acceptance intent from one exact official OpenSpec Change
projection and SHALL NOT require a tracked Commitment carrier or another
authored intent schema.

#### Scenario: Acceptance intent is compiled

- **WHEN** an official OpenSpec Change is selected from an exact Git tree
- **THEN** its requirements and scenarios deterministically compile one immutable Commitment value
- **AND** no `commitment.toml` or equivalent duplicate carrier is read or written

### Requirement: History and inquiry remain projections, not runtime authority

ETHOS SHALL NOT persist predecessor/successor lineage or hypothesis/falsifier/
experiment protocol state in Commitment, Lease, or a parallel lifecycle.

#### Scenario: Earlier work affects current admission

- **WHEN** a prior result is required for the current transition
- **THEN** the current TransitionPlan binds an exact valid Attestation for that result
- **AND** ordinary history remains derivable from Git and archived OpenSpec

#### Scenario: A Change contains a hypothesis or experiment procedure

- **WHEN** an author records a proposal, falsification criterion, or experiment procedure
- **THEN** it remains official OpenSpec design/spec/task content
- **AND** exact observations and conclusions are recorded only as Attestations
- **AND** no experiment state machine or Commitment DSL is created

### Requirement: Lease stores only expiring coordination

A Lease SHALL contain only lane identity, holder identity, CAS generation, and
expiry; it SHALL NOT mirror Git, OpenSpec, Commitment, workflow, or effect
state.

#### Scenario: An owned Work Lane advances

- **WHEN** the lane ref moves while the same holder retains coordination
- **THEN** current HEAD, tree, index, changed paths, and intent are re-observed as fresh Facts
- **AND** the Lease is not rewritten to mirror those facts

### Requirement: One executor owns each local repository ref effect

Every governed local ref mutation SHALL be executed by one TransitionPlan-bound
repository-effect owner that performs effect-time re-observation, exact CAS,
post-observation, Attestation persistence, and bounded compensation or recovery.

#### Scenario: A local ref effect succeeds

- **WHEN** an admitted plan's exact preconditions still match
- **THEN** the executor applies the declared CAS
- **AND** the post-observation and effect Attestation bind the same plan digest

#### Scenario: A lifecycle command requests a ref effect

- **WHEN** start, land, accepted closeout, refresh, holder transfer, takeover, or retirement needs a local ref mutation
- **THEN** it compiles its semantic authority into the common executor
- **AND** it does not own a parallel ref recovery state machine

### Requirement: Hooks never own Lease transition effects

The reference-transaction hook SHALL validate exact intent and observe Git ref
outcomes without advancing, revoking, or replacing Lease authority.

#### Scenario: An ordinary owned Work Lane commit moves its ref

- **WHEN** Git commits the branch ref after pre-commit authoring admission
- **THEN** the hook does not rewrite Lease state
- **AND** subsequent authority reads bind the stable Lease/Commitment generation to fresh branch HEAD and tree Facts

### Requirement: Rebuildable projections converge after the authority effect

Worktrees, indexes, hooks, and runtime files SHALL remain projections of an
attested Git ref effect rather than participants in a simulated cross-domain
transaction.

#### Scenario: Projection fails after an exact ref effect

- **WHEN** the ref CAS and its Attestation succeed but projection does not
- **THEN** the ref remains at the attested target
- **AND** retry recognizes that exact Attestation and completes the projection forward
- **AND** no reverse ref mutation is attempted

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
