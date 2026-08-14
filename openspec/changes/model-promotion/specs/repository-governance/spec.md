## REMOVED Requirements

### Requirement: Evidence-backed Claims

**Reason**: Claim duplicates the Attestation evidence envelope.

**Migration**: Express the assertion as an Attestation predicate and payload.

### Requirement: Evolution Governance

**Reason**: Campaign and Claim fields duplicate Commitment hypotheses and
Attestation observations.

**Migration**: Commitment owns hypotheses/protocols; Attestations own runs,
observations, results, and judgments.

### Requirement: Evolution Ledger Protocol

**Reason**: A mutable ledger creates a second currentness and selection owner.

**Migration**: Derive learning views from Commitments and Attestations.

### Requirement: Practice Selection And Fate

**Reason**: Practice Claims, candidate sets, evaluations, and fate records are
Attestation payloads and relations, not independent authorities.

**Migration**: Selection Attestations preserve judgments; successor Commitments
adopt normative effects.

### Requirement: Practice Evolution Kernel

**Reason**: Its useful contract is subsumed by Commitment protocols and
Attestation judgments without Claim or Chronicle promotion.

**Migration**: Use the two-root model and typed successor binding.

### Requirement: Trust-bearing Claim Admission

**Reason**: Trust evidence is an Attestation predicate with exact bindings.

**Migration**: Validate the bound Attestation in the operation authority query.

### Requirement: Claim evidence freshness is explicit

**Reason**: Attestation validity and bindings own freshness directly.

**Migration**: Use issued/valid times and exact semantic bindings.

### Requirement: Evolution Ledger Single Source Of Truth

**Reason**: There is no independent evolution truth store.

**Migration**: Use Commitment and the selected Attestation set.

### Requirement: Campaign Orchestration

**Reason**: Campaign state duplicates bounded OpenSpec Changes and task progress.

**Migration**: Use dependency-linked successor Commitments and one task graph per
Change.

### Requirement: Campaign Lifecycle Truth Is Carrier-Bound

**Reason**: Campaign lifecycle is a parallel projection that can disagree with
Git, Change, and Attestation facts.

**Migration**: Derive program views from the two-root model.

### Requirement: Canonical Persisted Claim Envelope

**Reason**: Attestation v2 is the sole persisted evidence envelope.

**Migration**: Historical Claim bytes remain inert; no current reader remains.

### Requirement: Campaign-terminal protected publication admission

**Reason**: Campaign state cannot authorize publication.

**Migration**: A successor publication Change shall consume exact Commitments,
Facts, plans, and Attestations.

## MODIFIED Requirements

### Requirement: Work Lane Lifecycle Resolution

Routine lifecycle SHALL remain mechanically derived from current facts and exact
plans. Exceptional interpretive judgment SHALL be an exact, non-authorizing
Attestation selected by the operation; Chronicle SHALL have no current reader or
producer.

#### Scenario: routine lifecycle remains local

- **WHEN** coordination is mechanically determined
- **THEN** ETHOS uses local Lease fencing and postcondition Attestations
- **AND** no tracked decision record is required

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** an exceptional destructive operation requires human judgment
- **THEN** a separately accepted Commitment and bound decision Attestation name
  exact target, evidence, disposition, recovery, and validity
- **AND** the operation re-observes mutable facts before its first effect

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** ownership, Lease, content, or recovery status is unknown or dirty
- **THEN** ETHOS preserves or blocks rather than inferring authority
- **AND** irreversible deletion requires exact accepted judgment and evidence

#### Scenario: break-glass reconciles after emergency action

- **WHEN** a predeclared break-glass Commitment admits an emergency effect
- **THEN** the result is an exact Attestation and later integration remains
  blocked until accepted reconciliation
- **AND** a self-supplied flag or holder string is insufficient

#### Scenario: lane handoff is recorded as Chronicle resolution

- **WHEN** an exceptional handoff judgment is required
- **THEN** it is recorded as a decision Attestation, not Chronicle
- **AND** it does not replace the destination-local Lease

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **WHEN** a lane has missing or ambiguous holder evidence
- **THEN** orphan-like facts remain observations and accepted disposition is an
  Attestation
- **AND** no persistent orphan or Chronicle state is created

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **WHEN** exact accepted judgment and evidence admit retirement
- **THEN** the resolver re-observes the source and emits an effect Attestation
- **AND** the authority does not extend to another lane or remote effect

## ADDED Requirements

### Requirement: Continuous intent preserves bounded Changes

Every accepted feedback occurrence SHALL be preserved in the Attestation set and
selected to a semantic owner or explicit absence, contradiction, or model-gap
disposition. New input SHALL NOT expand an active Commitment implicitly.

#### Scenario: Several agents provide concurrent feedback

- **WHEN** their inputs are independent
- **THEN** exact-CAS set union preserves every occurrence
- **AND** selections may feed disjoint successor Commitments

### Requirement: One Commitment binds one Change and lane generation

An effective Commitment SHALL bind one OpenSpec Change, one writable owner lane
generation, and one task authority. Successors MAY run concurrently only when
dependencies, scopes, and exact effects are disjoint.

#### Scenario: Input is deferred to a successor

- **WHEN** it cannot be completed inside the active boundary
- **THEN** selection and dependency remain traceable
- **AND** deferral does not count as implementation
