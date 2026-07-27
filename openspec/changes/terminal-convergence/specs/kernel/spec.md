## ADDED Requirements

### Requirement: Attestation Assurance Boundary

Semantic assurance SHALL be represented by an Attestation bound to the selected
ChangeContract digest, evidence digest, semantic scope, exact HEAD, verifier,
validity interval, and non-authorizing verdict. This boundary does not promote
ignored local postcondition receipts into Attestations, schemas, roots, or a
parallel lifecycle.

#### Scenario: Attestation is absent or mismatched

- **WHEN** the required assurance Attestation is missing, stale, repository-local,
  malformed, or bound to different facts
- **THEN** ETHOS fails the proposition closed with a machine-readable gap

#### Scenario: Digest-only proposition remains portable

- **WHEN** a ChangeContract contains a digest-only proposition
- **THEN** ETHOS requires no assurance service, account, daemon, credential,
  network operation, or dedicated local root

#### Scenario: Semantic attestation has a current semantic scope

- **WHEN** a ChangeContract requires semantic assurance
- **THEN** the Attestation binds the declared semantic scope and exact HEAD
- **AND** scope or HEAD drift makes the Attestation stale

### Requirement: Executable Local-State Dataflow

Local events and indexes SHALL exist only when current product code produces and
consumes them. Repository history is derived from Git, OpenSpec archives, and
Attestations rather than a current Chronicle store.

#### Scenario: lifecycle declaration is loaded

- **WHEN** lifecycle declarations compile
- **THEN** they contain transition policy, lease operations, and PlanIR actions
- **AND** unused event models and event-locality rules are absent

#### Scenario: local state is initialized

- **WHEN** ETHOS initializes ignored local SQLite state
- **THEN** it creates only tables consumed by current behavior
- **AND** routine coordination postcondition receipts remain ignored local state
  and do not become Attestations
- **AND** unused event and historical-projection CRUD tables are absent

#### Scenario: ignored local state uses the current contract

- **WHEN** ETHOS initializes its coordination database
- **THEN** it validates only the current owned schema
- **AND** retired generic migration ledgers are not recreated

#### Scenario: Chronicle remains derived historical evidence

- **WHEN** a governance judgment becomes durable
- **THEN** the judgment is an Attestation and Chronicle remains a derived
  historical projection
- **AND** Chronicle supplies history but never authorizes a current effect
- **AND** deleting unused local event logs creates no parallel truth store

## MODIFIED Requirements

### Requirement: Minimal Semantic Kernel

ETHOS SHALL compile exactly
(ChangeContract, RepositoryFacts, prior Attestations) -> PlanIR -> new
Attestations. ChangeContract and Attestation are the only persistent semantic
entities; RepositoryFacts is freshly observed and PlanIR is transient.

#### Scenario: Repository operation is represented

- **WHEN** ETHOS evaluates a repository operation
- **THEN** the selected base ChangeContract, fresh RepositoryFacts, and prior
  Attestations compile one deterministic PlanIR
- **AND** repository-semantic outcomes are recorded only as new Attestations
- **AND** routine local coordination receipts remain ignored local state and do
  not become Attestations
- **AND** verifier-bounded propositions exist only inside a ChangeContract or
  Attestation

#### Scenario: semantic attestation remains optional and bounded

- **WHEN** a ChangeContract requires semantic assurance
- **THEN** a candidate-external Attestation binds the selected contract digest,
  evidence digest, semantic scope, and exact HEAD
- **AND** the Attestation names the verifier, basis, verdict, and validity interval
- **AND** it records mints_authority as false
- **AND** stale or mismatched assurance blocks the proposition
- **AND** digest-only propositions require no assurance provider

#### Scenario: Model Promotion remains canonically owned

- **WHEN** a compiler or projection emits model_promotion_required
- **THEN** it links to
  [canonical Model Promotion rule](../../../../../docs/governance/product-design-contract.md#model-promotion)
- **AND** the projection does not restate the adjudication algorithm
- **AND** this design delta does not assert runtime effect or retirement
  enforcement

### Requirement: Product Core Adopter Isolation

ETHOS SHALL keep adopter-specific domain names out of product Python code except
inside bounded comparative-assurance Attestations and explicit adopter fixtures.

#### Scenario: Product code is scanned

- **WHEN** architecture tests scan package source files
- **THEN** adopter names are absent from semantic product implementation code

## REMOVED Requirements

### Requirement: Semantic attestation is receipt-bound and non-authorizing

**Reason**: A receipt contract would duplicate the persistent Attestation entity.

**Migration**: All three assurance scenarios move to Attestation Assurance
Boundary.

**Replacement**: Attestation Assurance Boundary

**Scenario replacement**: Digest-only claim remains portable -> Digest-only proposition remains portable

### Requirement: Event entities require an executable dataflow

**Reason**: Event and Chronicle stores would create parallel current-state
owners.

**Migration**: All four dataflow and history scenarios move to Executable
Local-State Dataflow.

**Scenario replacement**: Chronicle remains authoritative evidence -> Chronicle remains derived historical evidence

**Replacement**: Executable Local-State Dataflow
