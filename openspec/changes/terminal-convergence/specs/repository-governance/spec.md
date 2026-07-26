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

### Requirement: Non-locking Git Observation
Read-only lifecycle observation MUST use one isolated Git execution profile with
optional locks disabled. Git effects and handoff import/export MUST retain their
normal mutation environment.

#### Scenario: A lane is observed during concurrent work
- **WHEN** ETHOS reads refs, worktree status, tracked differences, or untracked paths
- **THEN** every Git observation uses `GIT_OPTIONAL_LOCKS=0`, fixed locale, and
  isolated Git configuration
- **AND** no inherited repository override can redirect the observation

#### Scenario: A Git effect executes
- **WHEN** ETHOS updates a ref, worktree, hook, bundle, or configuration
- **THEN** the observation profile is not applied implicitly

### Requirement: Authorized Lease Takeover
A foreign Work Lane lease MAY change holder without a source-holder handoff only
through one explicitly authorized takeover bound to the exact branch, HEAD,
lease generation, current dirty-content digest, destination actor, and declared
source-session state. The effect MUST use one local compare-and-swap, increment
the lease epoch, preserve `mints_authority = false`, and emit the authorization
reference and source-state boundary in its receipt.

#### Scenario: The source controller is quiescent
- **WHEN** the destination actor supplies the exact lease tuple and dirty digest,
  an authorization reference, a reason, and `source_state = "quiesced"`
- **THEN** takeover atomically replaces the holder and increments the epoch

#### Scenario: The source session is lost
- **WHEN** current authority explicitly authorizes takeover with
  `source_state = "lost"`
- **THEN** the receipt preserves that the source quiescence was not directly
  observed rather than claiming a normal handoff

#### Scenario: Target state drifts before takeover
- **WHEN** the branch, HEAD, lease tuple, actor, or dirty-content digest differs
  from the authorized request
- **THEN** takeover blocks without changing the lease
