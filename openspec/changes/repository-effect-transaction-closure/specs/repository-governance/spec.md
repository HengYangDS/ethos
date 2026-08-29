## REMOVED Requirements

### Requirement: One Commitment binds one Change and lane generation

**Reason**: Binding a transient intent value to mutable Lease state conflates
semantic acceptance with coordination.

**Migration**: Compile one minimal Commitment from the selected official Change;
keep the Lease as the independent four-field holder relation.

### Requirement: Commitment rebind partial effects recover through the original receipt

**Reason**: Rebind is a retired parallel transaction caused by mirrored state.

**Migration**: Recover the owning repository effect from its exact plan and
Attestation without advancing a mirrored Commitment generation.

### Requirement: Change creation resolves lineage before effects

**Reason**: Persisted predecessor resolution duplicates Git and archived
OpenSpec history.

**Migration**: Use Git ancestry for ordinary lineage and bind only an exact prior
Attestation when it changes current admission.

### Requirement: Change start recovery preserves exact lineage

**Reason**: Successor-lineage recovery is not a terminal authority boundary.

**Migration**: Recover the exact Change-start Git effect and re-observe official
OpenSpec intent; retain no predecessor set or successor identity.

### Requirement: Change lineage permits concurrency without global serialization

**Reason**: Concurrency is decided by exact effect CAS and current facts, not a
persisted Change graph.

**Migration**: Derive history as a query and serialize only conflicting exact
repository effects.

### Requirement: Repository Commitment admission is precise and pre-effect

**Reason**: A repository-wide tracked Commitment is a second intent and identity
carrier.

**Migration**: Read repository identity from the strict profile and compile
Change acceptance only from official OpenSpec.

## MODIFIED Requirements

### Requirement: OpenSpec Lifecycle Contract Review

ETHOS SHALL compose official OpenSpec validation with one transient Commitment
compiled from each selected active Change. Official proposal, specs, design,
tasks, metadata, and configuration are the sole tracked intent and lifecycle
carriers; no `commitment.toml`, `scope.toml`, local template, or Change README is
required.

#### Scenario: Active OpenSpec Change is lifecycle complete

- **GIVEN** an active OpenSpec Change has every artifact required by its official schema
- **WHEN** ETHOS audits lifecycle or compiles a plan
- **THEN** it validates the official Change and deterministically compiles acceptance intent
- **AND** no parallel tracked carrier participates

#### Scenario: Active OpenSpec Change lacks its contract

- **WHEN** an official required artifact is missing, invalid, or incomplete
- **THEN** ETHOS reports the exact official artifact or task gap
- **AND** no bootstrap, claim, archive scan, or parallel metadata grants authority

### Requirement: Authoritative Adopter Material Change Scope Binding

ETHOS SHALL require every valid adopter declaration to carry a non-empty
`[openspec].material_paths` list. For changed paths matching that declaration,
prewrite, changed planning, and proof SHALL attribute the fresh paths to the same
single selected active official OpenSpec Change. The attribution is a fact, not
an authored scope or permission carrier.

#### Scenario: covered material path is admitted across all surfaces

- **GIVEN** exactly one valid active Change is selected
- **WHEN** prewrite, changed planning, or proof evaluates a declared material path
- **THEN** each surface reports the same Change attribution
- **AND** no parallel tracked carrier participates

#### Scenario: uncovered material path is rejected consistently

- **WHEN** no active Change can own a declared material path
- **THEN** every surface reports `openspec_active_change_missing`
- **AND** no proof gate or historical carrier substitutes for intent

#### Scenario: Commitment coverage is singular

- **WHEN** more than one active Change could own a declared material path
- **THEN** every surface reports the same ambiguous active-Change gap
- **AND** no `scope.toml`, Commitment field, archive, or unrelated Change authorizes the write

### Requirement: Continuous intent preserves bounded Changes

Every accepted feedback occurrence SHALL be preserved in the Attestation set and
selected to a semantic owner or explicit absence, contradiction, or model-gap
disposition. New input SHALL NOT expand an active Change implicitly.

#### Scenario: Several agents provide concurrent feedback

- **WHEN** their inputs are independent
- **THEN** exact-CAS set union preserves every occurrence
- **AND** selections may feed disjoint future official OpenSpec Changes

### Requirement: Candidate proof admission selects repository authority

ETHOS SHALL use one repository-transition proof query for readiness and mutation.
The query SHALL bind exact repository identity, HEAD, tree, proof policy, and the
applicable transient Commitment or verified archive effect. Candidate acceptance,
accepted publication, and control-replacement admission SHALL consume that query.

#### Scenario: Historical Work Lane proof is not applicable

- **WHEN** a proof is bound only to a retired Work Lane relation
- **THEN** it does not authorize a current repository transition
- **AND** it remains queryable as historical evidence

#### Scenario: Retired Work Lane leaves the only applicable proof

- **GIVEN** a verified archive effect and proof bind the exact repository, HEAD, tree, and current proof policy
- **WHEN** the active Change and former Work Lane no longer exist
- **THEN** repository transition selects that exact evidence without scanning an archived Commitment carrier
- **AND** no historical ownership is recreated

#### Scenario: Applicable proof conflict fails closed

- **WHEN** selected proof bindings disagree
- **THEN** ETHOS returns the first stable mismatch coordinate
- **AND** no repository effect is authorized

#### Scenario: Closeout readiness and apply share proof admission

- **WHEN** accepted-root closeout is evaluated without and with `--apply`
- **THEN** both evaluations query the same candidate HEAD and proof selector
- **AND** a proof-selection mismatch cannot appear only after apply is requested

#### Scenario: Wrong authority cannot satisfy candidate acceptance

- **WHEN** a proof names another repository, HEAD, tree, policy, or applicable authority
- **THEN** ETHOS rejects it with a specific mismatch coordinate
- **AND** does not infer authority from another proof on the same HEAD

### Requirement: Publication selects repository authority

ETHOS SHALL select the exact accepted-HEAD repository proof and bind its
repository identity, commit, tree, policy, and verdict.

#### Scenario: Historical or conflicting proof shares the HEAD

- **WHEN** several proofs share the accepted HEAD
- **THEN** only the exact applicable repository proof SHALL apply, or selection fails closed on conflict

### Requirement: Exact local Git object projection

A product commit or annotated release tag SHALL be created and signed once in
the local Git authority. ETHOS SHALL verify the selected local object's signature
and publish the exact existing object bytes. Transport authentication, provider
identity, and provider presentation SHALL remain separate observations.

#### Scenario: one signed commit reaches two peers

- **WHEN** one trusted local commit is published to two independent peers
- **THEN** both peer refs equal the local commit OID
- **AND** transport credentials do not enter product object identity

#### Scenario: one annotated tag reaches two peers

- **WHEN** one trusted local annotated tag is published to two independent peers
- **THEN** local and peer tag object OIDs, peeled commits, and trees are equal

#### Scenario: a new remote ref is created

- **WHEN** the target ref is absent
- **THEN** the plan binds Git's zero OID as the exact expected state

#### Scenario: tree-only equality is insufficient

- **WHEN** a peer object has the expected tree but a different object OID
- **THEN** publication parity fails closed
- **AND** ETHOS does not accept replay, re-signing, identity rewrite, or tree-only equivalence

#### Scenario: proof authority is exact

- **WHEN** publication selects a proof Attestation
- **THEN** the plan binds its exact ID, repository identity, commit, tree, gate-set policy digest, and verdict
- **AND** hook and receipt apply reject coordinate drift

### Requirement: Lifecycle effect finalization authorizes exact transition paths

ETHOS SHALL use one verified OpenSpec lifecycle-effect authority for Change
start, official archive, canonical-spec projection, and post-archive closeout.
The authority SHALL bind repository identity, the transient Commitment digest,
previous and resulting Git facts, exact changed paths, official OpenSpec result,
and terminal effect Attestation. Status, plan, prove, land, prewrite, and hooks
SHALL consume that same authority. A durable partial effect SHALL recover through
the same public operation by exact CAS.

#### Scenario: Exact archive transition is congruent across readers

- **WHEN** official OpenSpec archive completes and the Git effect Attestation binds the exact source and result
- **THEN** status, plan, prove, land, prewrite, and hooks attribute the finalization paths identically
- **AND** no reader requires a new active Change or archived Commitment carrier

#### Scenario: A committed archive is recovered after controller loss

- **WHEN** the exact archive Git effect is durable but its rebuildable projection is incomplete
- **THEN** retry recognizes the effect Attestation and completes projection forward
- **AND** it does not replay OpenSpec, reverse the ref, or create another product commit

#### Scenario: Missing or tampered archive authority fails closed

- **WHEN** the official result, exact Git facts, effect Attestation, or changed path set is missing, ambiguous, stale, or tampered
- **THEN** ETHOS reports the first exact missing coordinate and one public next command
- **AND** it does not infer authority from an archive path or historical lane

#### Scenario: Multi-commit Change start recovers its exact successor

- **WHEN** an exact Change-start Git effect is durable and later projection failed
- **THEN** retry recognizes the same plan and completes projection forward
- **AND** it creates no second commit, lineage record, or OpenSpec invocation

#### Scenario: Finalization state is classified before mutation

- **WHEN** finalization observes a missing, expired, foreign, or valid Lease
- **THEN** it reports that exact coordination state and its one public action
- **AND** it never assumes holder identity or edits SQLite directly

#### Scenario: Zero-effect failure has no compensation gap

- **WHEN** preflight fails before an effect
- **THEN** the receipt preserves the original failure and proves owned assets absent
- **AND** it reports no compensation failure for an effect that never occurred

#### Scenario: Hook observation cannot re-enter Git maintenance

- **WHEN** a reference transaction invokes admission while Git holds a ref lock
- **THEN** the hook performs only bounded read-only observations
- **AND** unavailable observation fails closed without re-entering maintenance
