## ADDED Requirements

### Requirement: Worktree Family
One ChangeContract MUST derive one Worktree Family with zero or more cooperative slots, at most two competitive variants, read-only research workers, and exactly one canonical family head eligible for candidate integration.

#### Scenario: Two alternative implementations compete
- **WHEN** both variants satisfy the same acceptance contract
- **THEN** a selection attestation chooses one canonical head, records absorbed intent, and leaves the losing variant in a retireable state

### Requirement: Adaptive Backpressure
Concurrency admission MUST derive from conflict density, host capacity, proof latency, queue age, candidate throughput, and recoverability rather than a fixed global WIP limit.

#### Scenario: Independent low-conflict changes are ready
- **WHEN** host and proof capacity are available and their declared scopes do not overlap
- **THEN** the scheduler may admit them concurrently even when three other changes exist

### Requirement: Candidate Compare-and-swap Train
Authoring and proof MAY run concurrently, but candidate advancement MUST be a short serialized compare-and-swap against the observed candidate head.

#### Scenario: Candidate advances during proof
- **WHEN** a proven family attempts to land against a stale candidate head
- **THEN** the update is rejected and the family refreshes and re-proves rather than overwriting candidate state

### Requirement: Provider-neutral Proposal Role
The self profile MUST publish only `main`, `dev`, and `proposal/*`; `candidate/dev` and `work/*` MUST remain local-only.

#### Scenario: A local authoring branch is selected for push
- **WHEN** its role is candidate or work
- **THEN** publication blocks before any remote mutation

### Requirement: Active OpenSpec Coverage Is Contract-owned
An adopter's material-path classification MUST be matched only against the
selected active ChangeContracts. There MUST be no bootstrap, repair, claim
binding, or archive-carrier exception in the active verdict.

#### Scenario: A legacy scope file exists
- **WHEN** the active ChangeContract covers the material path
- **THEN** the contract decides coverage and the legacy file cannot widen it

#### Scenario: A complete Change remains in the active directory
- **WHEN** a new material write matches its historical scope
- **THEN** the complete Change is visible to lifecycle review but cannot authorize the write
