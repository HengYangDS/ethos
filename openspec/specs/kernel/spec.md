# ETHOS Kernel

## Purpose

ETHOS SHALL model repository operation through Authority, Subject,
Commitment, Change, Evidence, Claim, and Chronicle.
## Requirements
### Requirement: Kernel Chain
ETHOS SHALL model repository operation through the kernel chain
Authority, Subject, Commitment, Change, Evidence, Claim, and Chronicle.
The chain SHALL preserve the root text as a judgment constraint without turning
that text into a subsystem, feature map, or low-level implementation label.
Commitment SHALL remain the governed promise that can become repository law;
practice claims and workflow runtime facts SHALL remain carriers or projections
that propose, test, or inspect effects on commitments.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through kernel objects without depending
  on repository, assistant, adapter, adopter, or hosted-runner packages
- **AND** Claim binds evidence rather than owning lifecycle state
- **AND** semantic claims require a current, candidate-external semantic attestation receipt

#### Scenario: semantic attestation remains optional and bounded

- **WHEN** a claim declares `semantic_attested`
- **THEN** it SHALL bind a candidate-external receipt to its claim id, dated-evidence digest, semantic scope digest, and exact HEAD
- **AND** the receipt SHALL name an independent reviewer role, basis, allow verdict, validity interval, and `mints_authority = false`
- **AND** missing, malformed, stale, repository-local, or mismatched receipts SHALL block the claim
- **AND** `digest_only` claims SHALL require no receipt directory, account, daemon, credential, network, or dedicated local account

#### Scenario: Root text remains canonical and restrained
- **WHEN** ETHOS adds or changes an active code, config, hook, system contract, or
  provider projection surface
- **THEN** that surface cites concrete engineering invariants rather than philosophical labels
  or numbered philosophy references
- **AND** the canonical root text remains in the Product Design Contract rather
  than being duplicated into machine-adjacent derived files
- **AND** derived axiom files remain subordinate to product docs and do not create
  a new truth center

#### Scenario: Workflow runtime stays below the kernel
- **WHEN** ETHOS evaluates workflow runtime state, handoff state, or skill eval metadata
- **THEN** the runtime facts are expressible through the kernel chain
- **AND** lifecycle truth is still derived from authority, subject, commitment, change, evidence, claim, and chronicle facts
- **AND** generated runtime state does not outrank source, tests, schemas, docs, OpenSpec records, claims, evidence, or command JSON

### Requirement: Kernel Result Contract
ETHOS SHALL emit stable JSON result envelopes with `ok`, `summary`,
`diagnostics`, `required_gaps`, `next_actions`, and `data`.

#### Scenario: Automation reads command output
- **WHEN** an automation consumer requests JSON output from an ETHOS command
- **THEN** the response is one parseable object with the stable result fields

### Requirement: Deterministic Action Graph
ETHOS SHALL serialize action graphs deterministically, including validation gaps
for invalid graphs.

#### Scenario: Proof readiness is planned
- **WHEN** ETHOS plans or runs proof gates
- **THEN** selected gates are represented as ordered action graph nodes with
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
