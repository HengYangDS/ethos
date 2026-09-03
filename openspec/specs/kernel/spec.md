# ETHOS Kernel

## Purpose

ETHOS SHALL persist only Commitment and Attestation semantic entities and
derive Facts and TransitionPlan.

## Requirements

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

#### Scenario: Lifecycle declarations compile directly into TransitionPlan
- **WHEN** ETHOS evaluates lifecycle, handoff, or skill-evaluation metadata
- **THEN** tracked declarations and current facts compile directly into TransitionPlan
- **AND** no parallel workflow-runtime read model or state store is required
- **AND** generated projections do not outrank source, tests, schemas, docs,
  OpenSpec records, attestations, evidence, or command JSON

### Requirement: Closed Verdict Reduction
ETHOS SHALL derive one public `verdict` from required facts and diagnostics.
The only values are `pass`, `block`, and `unknown`; missing or unverifiable
required facts produce `unknown`, while conflicts, explicit failures, and
warnings produce `block`. Only `pass` may authorize an effect.

#### Scenario: Required facts reduce to a closed verdict
- **WHEN** ETHOS reduces current required facts and diagnostics
- **THEN** missing or unverifiable required facts produce `unknown`, conflicts,
  explicit failures, or warnings produce `block`, and only `pass` authorizes an
  effect
- **AND** the result has no top-level `ok` field

### Requirement: Kernel Result Contract
ETHOS SHALL emit schema-version-`2` JSON result envelopes with `verdict`,
`state`, `summary`, `diagnostics`, `required_gaps`, singular `next_action`,
`user_decision_required`, and `data`. `continuation` and
`missing_facts_or_evidence` are derived fields, not lifecycle state.

#### Scenario: Automation reads command output
- **WHEN** an automation consumer requests JSON output from an ETHOS command
- **THEN** the response is one parseable schema-version-`2` object with the
  stable result fields
- **AND** it preserves `state` and `required_gaps`, has no plural action field,
  and derives exactly one `continuation` value
- **AND** `missing_facts_or_evidence` equals `required_gaps` only for an
  `unknown` verdict

### Requirement: Deterministic TransitionPlan
ETHOS SHALL serialize TransitionPlan deterministically, including validation gaps
for invalid dependency sets.

#### Scenario: Proof readiness is planned
- **WHEN** ETHOS plans or runs proof gates
- **THEN** selected gates are represented as ordered TransitionPlan nodes with
  explicit dependencies and validation gaps

### Requirement: Physical Target Product Homes
ETHOS SHALL provide buildable target product package homes for the semantic kernel,
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

### Requirement: Semantic identity is schema-versioned and runtime-independent

A supported semantic carrier SHALL be interpreted by exactly one immutable
schema-version protocol. Identity-bearing defaults, normalization, canonical
projection, and digest domain SHALL NOT vary between source, wheel, package-only
runtime, host, or process. Semantic collection input order SHALL NOT determine
validity or identity; the contract owner SHALL validate members and normalize
them before identity projection. Every JSON value used to derive semantic
identity, an authority-bearing signature payload, or an admission digest SHALL
use the same kernel-owned closed canonical byte projection. Exact raw-content,
Git-object, native-program, and presentation bytes SHALL remain under their
native owners and SHALL NOT redefine semantic JSON identity.

#### Scenario: The same v2 carrier is interpreted in several runtimes

- **WHEN** exact bytes are loaded from the same Git tree
- **THEN** every runtime produces the same semantic identity
- **AND** a changed interpreter requires a new schema version

#### Scenario: A current v1 carrier is encountered after cutover

- **WHEN** normal plan compilation or mutation loads it
- **THEN** ETHOS blocks before deriving current semantic authority
- **AND** only the exact one-shot bootstrap may consume its persisted Lease tuple

#### Scenario: Equivalent collection permutations are loaded

- **WHEN** two supported carriers contain the same valid semantic collection
  members in different physical orders
- **THEN** both produce the same typed value, canonical JSON, and digest
- **AND** repeated canonical projection is idempotent

#### Scenario: A semantic collection contains duplicate or conflicting members

- **WHEN** normalization observes a duplicate identity or a field-specific
  semantic conflict
- **THEN** ETHOS rejects the carrier before deriving authority
- **AND** sorting never hides or resolves the conflict

#### Scenario: Semantic JSON identity crosses entry paths

- **WHEN** equivalent valid JSON meaning reaches Commitment, Attestation, Facts,
  TransitionPlan, policy, rule, or independent-verification identity through
  different public entry paths
- **THEN** every path consumes the same canonical UTF-8 bytes
- **AND** Unicode object keys use the one declared ordering
- **AND** values outside the closed semantic grammar fail before hashing or
  signing

#### Scenario: A composed admission projection binds exact observations

- **WHEN** an admission projection contains exact raw-file, Git-entry, or
  implementation digests as members
- **THEN** those nested digests continue to identify their native bytes
- **AND** the enclosing typed admission projection uses the one semantic JSON
  byte protocol

#### Scenario: Exact canonical bytes are required by a storage boundary

- **WHEN** a reader consumes an already content-addressed canonical JSON envelope
- **THEN** it MAY reject byte-level non-canonical representation
- **AND** that check SHALL NOT make ordinary typed input order semantically invalid

#### Scenario: Non-semantic bytes are bound

- **WHEN** ETHOS hashes a raw file, wheel, runtime inventory member, Git object,
  Git transaction program, or rendered output
- **THEN** the native owner hashes the exact relevant bytes
- **AND** the semantic JSON canonicalizer does not normalize or reinterpret them

#### Scenario: A projected checksum has no identity consumer

- **WHEN** a report or normalized projection emits a checksum that no current
  comparison, lookup, signature, CAS, or validation consumes
- **THEN** the checksum and any schema or prose requiring it are removed
- **AND** the underlying typed projection remains available to its real readers

### Requirement: Unknown semantic input is lossless and non-authorizing

The kernel SHALL preserve structurally canonical unknown predicates, payloads,
and relations. Only values understood by the selected operation evaluator MAY
satisfy an authority query.

#### Scenario: A future input kind is received

- **WHEN** its canonical envelope is valid but its semantic kind is unknown
- **THEN** ETHOS round-trips it without reinterpretation
- **AND** it cannot authorize an effect or satisfy required evidence
