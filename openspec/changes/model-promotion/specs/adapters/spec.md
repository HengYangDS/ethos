## REMOVED Requirements

### Requirement: Work Lane Claim Binding Projection

**Reason**: Claim binding duplicates the lane-bound Commitment and exact
Attestation query.

**Migration**: Status projects the selected Commitment, Lease facts, and exact
Attestation results without a Claim ID.

## MODIFIED Requirements

### Requirement: Lease-backed Lane Start

ETHOS SHALL acquire one local Lease generation and bind one explicit Commitment
when creating a Work Lane through the public command plane. Raw Git worktree
creation is not governed Work Lane state because it has neither binding.

#### Scenario: Work Lane start is applied

- **WHEN** the public command creates a lane from a valid Commitment
- **THEN** it creates the exact worktree/ref and one Git-common Lease generation
- **AND** no Claim boundary is created or required

#### Scenario: Existing Change continuation is applied

- **WHEN** lane start explicitly continues from a clean owned Work Lane
- **THEN** ETHOS copies its exact Lease-bound Commitment carrier
- **AND** it does not evaluate fresh bootstrap

#### Scenario: Work Lane start intent is absent or ambiguous

- **WHEN** neither a Commitment nor source Work Lane is supplied, or both are
  supplied
- **THEN** ETHOS blocks before creating a worktree, Lease, or ref

#### Scenario: Work Lane start is requested from a non-accepted or dirty root

- **WHEN** lane start runs from an existing Work Lane or dirty accepted root
- **THEN** ETHOS blocks before mutation

### Requirement: Bounded External Evidence Adapters

External identity, hosted-enforcement, and control-replacement evidence SHALL be
validated only when the selected Commitment requires its exact Attestation
predicate and bindings. An external adapter stores no credentials and mints no
authority.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof, schema, hook, identity, or
  enforcement controls
- **THEN** closeout requires candidate-external proof and decision Attestations
  binding both heads, control digests, verifier digest, proof digest, and
  decision identity
- **AND** a hand-authored summary or historical Chronicle cannot satisfy it

#### Scenario: Control removal and branch-role changes cannot evade admission

- **WHEN** a candidate deletes, renames, or changes a declared control
- **THEN** closeout requires the same exact Attestation query
- **AND** an unavailable diff blocks rather than returning pass

#### Scenario: hosted prevention requires exact receipt

- **WHEN** ETHOS claims hosted prevention
- **THEN** a provider receipt Attestation binds remote, commit, tree, action,
  proof and policy digests, verifier, issuer, validity, and signature
- **AND** local hooks or provider configuration alone do not prove prevention

#### Scenario: independent re-execution requires an exact signed receipt

- **WHEN** ETHOS projects independent re-execution
- **THEN** the exact signed receipt Attestation binds the same hosted facts
- **AND** local re-execution alone does not satisfy the hosted predicate

#### Scenario: provider-local reference implementation is physically bounded

- **WHEN** an operator enables external verification
- **THEN** its executable remains outside ETHOS product source and distribution
- **AND** it consumes the provider-neutral Attestation contract

#### Scenario: Generic Git server enforcement is disabled by default

- **WHEN** no provider-local adapter is enabled
- **THEN** ordinary local governance requires no account, key, daemon, or store
- **AND** no missing provider adapter mints or removes authority

#### Scenario: A protected generic Git update has an exact independent receipt

- **WHEN** an enabled adapter receives a protected update
- **THEN** it admits only an exact valid signed provider receipt Attestation
- **AND** malformed, stale, failed, unsigned, or mismatched evidence blocks

#### Scenario: An update is outside the configured protected set

- **WHEN** a provider adapter receives an update outside its protected set
- **THEN** it does not require the hosted predicate for that ref
- **AND** it does not infer policy from the proposed tree

#### Scenario: The server adapter remains a thin physical extension

- **WHEN** any Forge or generic Git provider projects enforcement
- **THEN** it conforms to the same Attestation query
- **AND** it does not become a second governance kernel

### Requirement: Intake Adapter Projection Boundary

Intake and Backlog provider state SHALL remain input Attestations or read-only
projection rather than repository truth.

#### Scenario: Intake provider reports done state

- **WHEN** an intake provider reports a task complete
- **THEN** the occurrence may be preserved and selected for a successor
  Commitment
- **AND** it does not replace OpenSpec readiness, executed proof, or exact
  operation Attestation queries

### Requirement: Optional tool adapters remain replaceable

Optional runners, graph systems, task ledgers, workflow frameworks, and method
packs MAY project into Commitment, Attestation, Facts, or derived plans. Their
commands, hidden stores, task state, and phase names SHALL NOT become ETHOS
lifecycle or semantic roots.

#### Scenario: Adapter profile is reported

- **WHEN** an optional adapter emits a result
- **THEN** it remains an input or derived projection
- **AND** it cannot replace Commitment, Attestation, proof, or Git-native Work
  Lane semantics

#### Scenario: External workflow frameworks are classified

- **WHEN** ETHOS evaluates an external workflow framework
- **THEN** useful values may map into the two-root model or derived plans
- **AND** the framework command plane and hidden state remain non-authoritative

## ADDED Requirements

### Requirement: Attestations use one deterministic Git set carrier

The sole current Attestation carrier SHALL be a canonical hash-sharded Git tree
selected by `refs/ethos/attestations-set`. Its root SHALL be a deterministic
parentless commit over fixed metadata. An update SHALL be exactly the union of
the observed set and validated canonical members followed by exact CAS.

#### Scenario: Concurrent writers add different Attestations

- **WHEN** one writer loses the set-ref CAS race
- **THEN** it re-observes the selected set and recomputes the deterministic union
- **AND** the successful root contains both immutable members

#### Scenario: A member is added repeatedly or collides

- **WHEN** canonical bytes for an existing identity are added again
- **THEN** the root is unchanged
- **AND** different bytes for the same identity fail closed

#### Scenario: Set membership is evaluated

- **WHEN** an Attestation exists in the selected set
- **THEN** membership proves preservation only
- **AND** an operation still validates predicate, payload, relations, verifier,
  bindings, validity, and selected Commitment

### Requirement: Non-authoritative Attestation stores are not current readers

Git-common JSON directories and operation indexes MAY stage or cache bytes but
SHALL NOT select current Attestations or authorize effects after cutover.
Historical Claim and Chronicle bytes SHALL remain inert Git history.

#### Scenario: A stale local Attestation exists

- **WHEN** it is absent from the selected Git set
- **THEN** status, planning, proof, and effects ignore it as current evidence
- **AND** no compatibility scan silently promotes it
