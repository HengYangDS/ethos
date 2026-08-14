## MODIFIED Requirements

### Requirement: Minimal Semantic Kernel

ETHOS SHALL persist exactly Commitment and Attestation as semantic roots. Facts
and `TransitionPlan` SHALL remain derived. No Claim, Chronicle, Ledger, Campaign,
shared inbox, Lease, ref, task, or stored plan SHALL own normative intent or
reusable authority.

#### Scenario: Repository operation is represented

- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through Commitment, Attestation, Facts,
  and `TransitionPlan` without higher-layer semantic owners
- **AND** Attestations bind evidence without minting authority

#### Scenario: semantic attestation remains optional and bounded

- **WHEN** semantic assurance rather than digest-only proof is required
- **THEN** assurance is a candidate-external, non-authorizing Attestation bound
  to subject, scope, exact HEAD, verifier, verdict, and validity
- **AND** digest-only proof requires no external account or network

### Requirement: Semantic attestation is receipt-bound and non-authorizing

ETHOS SHALL admit assurance only by validating one Attestation v2 whose
predicate, payload, relations, verifier, validity, exact bindings, and selected
Commitment satisfy the operation query. Membership and digest equality alone
SHALL NOT satisfy the query.

#### Scenario: Attestation is absent or mismatched

- **WHEN** an Attestation is missing, stale, structurally unknown to the
  evaluator, or mismatched
- **THEN** the operation fails closed with a machine-readable gap
- **AND** no Claim mode or receipt-directory fallback is consulted

#### Scenario: Digest-only claim remains portable

- **WHEN** an operation requires only digest-bound proof
- **THEN** it does not require or inspect a semantic receipt directory, account,
  daemon, credential, network operation, or dedicated user
- **AND** no Claim compatibility mode is created

#### Scenario: Semantic attestation has a current semantic scope

- **WHEN** an operation requires semantic assurance
- **THEN** the Attestation binds exact subject, semantic scope, and current HEAD
- **AND** validity and operation-specific predicate evaluation remain required

### Requirement: Event entities require an executable dataflow

ETHOS SHALL retain a durable event-like value only as an Attestation consumed by
a current evaluator or derived projection. Declaration-only streams, generic
event logs, Campaign state, mutable inbox state, and Chronicle authority SHALL
be absent.

#### Scenario: lifecycle declaration is loaded

- **WHEN** lifecycle declaration is validated and projected
- **THEN** it contains only currently consumed transition and Lease policies
- **AND** no Campaign or generic event owner is emitted

#### Scenario: local state is initialized

- **WHEN** ignored local state is created
- **THEN** it creates only tables consumed by current behavior
- **AND** generic event and Chronicle CRUD is absent

#### Scenario: ignored local state uses the current contract

- **WHEN** ETHOS initializes disposable coordination state
- **THEN** it creates only the current Lease contract
- **AND** no migration ledger or retired local format persists

#### Scenario: Git-common state stays outside checkouts

- **WHEN** ETHOS resolves mutable state for any linked worktree
- **THEN** staging, cache, and Lease state use the shared Git common directory
- **AND** no checkout gains untracked runtime truth

#### Scenario: Chronicle remains authoritative evidence

- **WHEN** a governance decision becomes durable
- **THEN** it is one Attestation v2 in the sole set, not Chronicle
- **AND** no campaign CEL, event table, migration ledger, acknowledgement,
  consumed flag, or inbox cursor is created

## ADDED Requirements

### Requirement: Semantic identity is schema-versioned and runtime-independent

A supported semantic carrier SHALL be interpreted by exactly one immutable
schema-version protocol. Identity-bearing defaults, normalization, canonical
projection, and digest domain SHALL NOT vary between source, wheel, package-only
runtime, host, or process.

#### Scenario: The same v2 carrier is interpreted in several runtimes

- **WHEN** exact bytes are loaded from the same Git tree
- **THEN** every runtime produces the same semantic identity
- **AND** a changed interpreter requires a new schema version

#### Scenario: A current v1 carrier is encountered after cutover

- **WHEN** normal plan compilation or mutation loads it
- **THEN** ETHOS blocks before deriving current semantic authority
- **AND** only the exact one-shot bootstrap may consume its persisted Lease tuple

### Requirement: Unknown semantic input is lossless and non-authorizing

The kernel SHALL preserve structurally canonical unknown predicates, payloads,
and relations. Only values understood by the selected operation evaluator MAY
satisfy an authority query.

#### Scenario: A future input kind is received

- **WHEN** its canonical envelope is valid but its semantic kind is unknown
- **THEN** ETHOS round-trips it without reinterpretation
- **AND** it cannot authorize an effect or satisfy required evidence
