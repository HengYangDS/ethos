# ETHOS Kernel

## Purpose

ETHOS SHALL persist only ChangeContract and Attestation semantic entities and
derive RepositoryFacts and PlanIR.
## Requirements
### Requirement: Minimal Semantic Kernel

ETHOS SHALL model repository operation through ChangeContract, Attestation,
RepositoryFacts, and PlanIR without parallel semantic entity owners.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through the minimal kernel without depending
  on repository, assistant, adapter, adopter, or hosted-runner packages
- **AND** attestations bind evidence without owning reusable authority
- **AND** semantic claims require a current, candidate-external semantic attestation receipt

#### Scenario: semantic attestation remains optional and bounded

- **WHEN** a claim declares `semantic_attested`
- **THEN** it SHALL bind a candidate-external receipt to its claim id, dated-evidence digest, semantic scope digest, and exact HEAD
- **AND** the receipt SHALL name an independent reviewer role, basis, allow verdict, validity interval, and `mints_authority = false`
- **AND** missing, malformed, stale, repository-local, or mismatched receipts SHALL block the claim
- **AND** `digest_only` claims SHALL require no receipt directory, account, daemon, credential, network, or dedicated local account

### Requirement: Root Interpretation Boundary

The kernel chain SHALL preserve the root text as a judgment constraint. It
SHALL NOT turn that text into a subsystem, feature map, or low-level implementation label.

#### Scenario: Root text remains canonical and restrained
- **WHEN** ETHOS adds or changes an active code, config, hook, system contract, or
  provider projection surface
- **THEN** that surface cites concrete engineering invariants rather than philosophical labels
  or numbered philosophy references
- **AND** the canonical root text remains in the Product Design Contract rather
  than being duplicated into machine-adjacent derived files
- **AND** derived axiom files remain subordinate to product docs and do not create
  a new truth center

#### Scenario: Lifecycle declarations compile directly into PlanIR
- **WHEN** ETHOS evaluates lifecycle, handoff, or skill-evaluation metadata
- **THEN** tracked declarations and current facts compile directly into PlanIR
- **AND** no parallel workflow-runtime read model or state store is required
- **AND** generated projections do not outrank source, tests, schemas, docs,
  OpenSpec records, attestations, evidence, or command JSON

### Requirement: Kernel Result Contract
ETHOS SHALL emit stable JSON result envelopes with `ok`, `summary`,
`diagnostics`, `required_gaps`, `next_actions`, and `data`.

#### Scenario: Automation reads command output
- **WHEN** an automation consumer requests JSON output from an ETHOS command
- **THEN** the response is one parseable object with the stable result fields

### Requirement: Deterministic PlanIR
ETHOS SHALL serialize PlanIR deterministically, including validation gaps
for invalid dependency sets.

#### Scenario: Proof readiness is planned
- **WHEN** ETHOS plans or runs proof gates
- **THEN** selected gates are represented as ordered PlanIR nodes with
  explicit dependencies and validation gaps

### Requirement: Physical Target Product Homes
ETHOS SHALL provide buildable target product package homes for core,
contracts, repository semantics, assistants, adapters, CLI, and conformance
proof.

#### Scenario: Target package homes are audited
- **WHEN** architecture tests inspect product package topology
- **THEN** each target package has package metadata and a canonical README
- **AND** semantic target packages do not import provider execution modules

### Requirement: Product Core Adopter Isolation
ETHOS SHALL keep adopter-specific domain names out of product Python code except
for explicit parity contract records.

#### Scenario: Product code is scanned
- **WHEN** architecture tests scan package source files
- **THEN** adopter names are absent from semantic product implementation code

### Requirement: Semantic attestation is receipt-bound and non-authorizing

ETHOS SHALL admit `semantic_attested` only when a typed candidate-external
receipt binds the exact claim, dated evidence digest, semantic promotion scope,
and current HEAD. The receipt SHALL record an independent reviewer role, basis,
allow verdict, validity interval, canonical payload digest, and
`mints_authority = false`.

#### Scenario: Attestation is absent or mismatched

- **WHEN** the claim-side declaration or external receipt is missing,
  malformed, stale, repository-local, or does not match a bound fact
- **THEN** ETHOS SHALL fail the claim closed with a machine-readable gap

#### Scenario: Digest-only claim remains portable

- **WHEN** a claim declares `digest_only`
- **THEN** ETHOS SHALL not require or inspect a semantic receipt directory,
  account, daemon, credential, network operation, or dedicated local account

#### Scenario: Semantic attestation has a current semantic scope

- **WHEN** a claim declares `semantic_attested`
- **THEN** its evidence freshness mode SHALL be `semantic_scope`
- **AND** its receipt scope and HEAD bindings SHALL match that current scope

### Requirement: Event entities require an executable dataflow

ETHOS SHALL retain an event entity only when a tracked production path creates
it and a tracked consumer, reducer, or evidence boundary uses it. Declaration-
only streams and unused local event logs SHALL be absent.

#### Scenario: lifecycle declaration is loaded

- **WHEN** the lifecycle declaration is validated and projected
- **THEN** it SHALL contain only transition policies, lease operations, PlanIR
  actions, and campaign CEL consumed by current product behavior
- **AND** no event model, event count, or event-locality rule without a producer
  and consumer SHALL be emitted.

#### Scenario: local state is initialized

- **WHEN** ETHOS initializes ignored local SQLite state
- **THEN** it SHALL create only tables consumed by current product behavior
- **AND** unused generic event and chronicle-event tables and CRUD APIs SHALL be absent.

#### Scenario: ignored local state uses the current contract

- **WHEN** ETHOS initializes its disposable coordination database
- **THEN** it SHALL create only the current lease table
- **AND** it SHALL NOT preserve schema migration ledgers or retired local formats.

#### Scenario: Chronicle remains authoritative evidence

- **WHEN** a governance decision becomes durable
- **THEN** its Chronicle evidence SHALL remain governed by repository evidence contracts
- **AND** removing unused SQLite event logs SHALL NOT create a parallel event bus or truth store.
