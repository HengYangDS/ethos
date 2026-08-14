## REMOVED Requirements

### Requirement: Campaign Orchestration

**Reason**: Campaign manifests and commands duplicate OpenSpec Change tasks and
create a second lifecycle/progress state machine.

**Migration**: One active Change's `tasks.md` is the complete dependency-ordered
work graph. Status derives current progress from that carrier and evidence.

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

**Reason**: Campaign step states are redundant projections that can disagree
with Change, Git, proof, and closeout facts.

**Migration**: Derive all lifecycle views from Commitment, fresh Facts, the
Change task carrier, and Attestations.

### Requirement: Campaign-terminal protected publication admission

**Reason**: Publication admission must consume exact local and peer transition
receipts, not Campaign state.

**Migration**: Use receipt-bound local closeout and independent peer projection
Attestations.

## ADDED Requirements

### Requirement: Repository lifecycle has one transition owner

Lane start, refresh, rebind, handoff, land, role transition, retirement, history
replacement, runtime migration, proof, and publication SHALL be operation
declarations reduced and applied by the same transaction spine.

#### Scenario: A lifecycle command family is inspected

- **WHEN** architecture tests trace its policy, authority, mutation, recovery,
  and result paths
- **THEN** exactly one reducer and one effect engine own those semantics
- **AND** command-local state machines and reusable permission checks are absent

### Requirement: Coordination is demand-driven fencing

Single-person serial work SHALL require no synthetic coordination entity.
Work Lane, Lease, and controller fencing SHALL appear only when concurrent
writers, worktrees, processes, or hosts create a concrete exclusion need.
Shared inbox and reusable controller progress state SHALL NOT remain.

#### Scenario: One actor works serially in one checkout

- **WHEN** no competing writer or detached carrier exists
- **THEN** the repository lifecycle proceeds without a shared inbox or durable
  controller state

#### Scenario: Multiple local processes or worktrees contend

- **WHEN** two operations target an overlapping exact resource generation
- **THEN** Lease generation and receipt CAS fence the second operation
- **AND** disjoint declared resources may proceed independently

#### Scenario: Work moves to another host

- **WHEN** a different Git common directory receives the work
- **THEN** content and attestations transfer while destination-local fencing is
  newly derived
- **AND** ETHOS does not claim a distributed Lease or cross-host atomicity

### Requirement: Candidate is an optional integration resource

Candidate SHALL be profile-selected and MAY be absent or short-lived. Proposal
source identity SHALL bind a proved OID and exact target baseline, not a required
candidate branch name.

#### Scenario: Repository uses direct local acceptance

- **WHEN** policy omits a persistent candidate role
- **THEN** a proved work result may compile directly to the declared accepted
  transition without inventing a candidate branch

#### Scenario: Proposal is created from a proved result

- **WHEN** the source OID and target baseline are exact
- **THEN** proposal derivation is independent of the local branch name that
  happens to reference the source OID

### Requirement: Complete DAG semantic replacement is governed

ETHOS SHALL validate and exact-CAS a complete replacement graph under a
repository-declared semantic equivalence, actor, signature, and trust policy.
Tree, ordered parents, topology, timestamps, control refs, Lease, Commitment,
proof, and rollback bindings SHALL be exact; declared message, actor, and
signature fields MAY differ.

#### Scenario: Replacement graph is semantically equivalent

- **WHEN** every graph invariant and trusted projection receipt passes
- **THEN** ETHOS may advance the declared control refs through one receipt
- **AND** local and provider identity domains remain independently attested

#### Scenario: Same-holder identity or semantic repair is requested

- **WHEN** the current holder supplies an exact replacement graph and policy
- **THEN** one receipt distinguishes signature-only identity repair from
  declared semantic-field replacement
- **AND** both paths bind complete graph equivalence, control refs, proof, and
  rollback before CAS

### Requirement: Divergent retirement is evidence-bound and MECE

Retirement SHALL distinguish accepted-absorbed, candidate-absorbed,
successor-absorbed, and intentionally abandoned lanes. Missing or expired Lease
retirement requires explicit maintainer authority and exact clean carrier,
worktree, ref, semantic evidence, and preservation observations.

#### Scenario: Clean lane is absorbed only by candidate

- **WHEN** the exact Work Lane head is an ancestor of the configured candidate
  but not accepted
- **THEN** owner retirement may issue a candidate-absorbed receipt
- **AND** an active foreign owner remains fail closed

### Requirement: Role transitions bind source and target worktrees

Role-transition policy SHALL be compiled from the exact source tree and bind the
common Git repository identity, source checkout, target ref and checkout,
proof, and exact old/new heads.

#### Scenario: Accepted and release roles use distinct worktrees

- **WHEN** a declared accepted-to-release edge is applied
- **THEN** ETHOS exact-CAS advances the target ref and synchronizes its worktree
- **AND** the target's older policy tree does not replace source policy

#### Scenario: Candidate closes out to accepted

- **WHEN** exact proof and source-tree policy authorize the transition
- **THEN** land advances the declared accepted role, updates its worktree, and
  records Lease disposition in one receipt
- **AND** an archived Change proof is not rejected for using a different
  repository Commitment digest class

### Requirement: Provider proposals are peer-native projections

Each provider proposal SHALL start from that peer's exact native target
baseline, replay only canonical successors under its declared identity and
signing policy, and produce an independent projection receipt before push.

#### Scenario: Canonical candidate has no merge base with peer target

- **WHEN** no valid semantic projection receipt maps the histories
- **THEN** proposal creation blocks before push

### Requirement: Local and peer acceptance remain explicit

ETHOS SHALL support local-only, GitLab-only, GitHub-only, dual-peer, and
arbitrary declared peer topologies around one canonical accepted OID. Each peer
executes its own Plan, Effect, and Attestation; partial success SHALL remain
visible and SHALL NOT be described as cross-provider atomicity.

#### Scenario: One of two peers succeeds

- **WHEN** one peer accepts or publishes and another blocks or drifts
- **THEN** the successful peer Attestation is preserved independently
- **AND** the repository reports the remaining peer continuation without
  rolling back or overstating the successful peer

#### Scenario: Remote merge result is ingested

- **WHEN** a provider produces a protected target OID
- **THEN** ingestion verifies its exact baseline, tree/semantic mapping, proof,
  and peer Attestation before advancing canonical local roles
