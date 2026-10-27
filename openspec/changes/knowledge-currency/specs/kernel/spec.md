## MODIFIED Requirements

### Requirement: Minimal Semantic Kernel

ETHOS SHALL keep exactly Commitment and Attestation as semantic roots; only
Attestation SHALL persist. Commitment SHALL remain transient acceptance compiled
from one exact official OpenSpec Change, and Facts and `TransitionPlan` SHALL
remain transient and derived. No Claim, Chronicle, Ledger, Campaign,
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

#### Scenario: Commitment is compiled, not stored

- **WHEN** ETHOS needs a Change's acceptance meaning
- **THEN** it compiles the Commitment from the exact Git-tree projection of the
  official OpenSpec Change
- **AND** no Commitment record, path, relation graph or workflow state persists

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

- **WHEN** ETHOS evaluates declared gates or a lane lifecycle effect
- **THEN** tracked declarations and current facts compile directly into TransitionPlan
- **AND** no parallel workflow-runtime read model or state store is required
- **AND** generated projections do not outrank source, tests, schemas, docs,
  OpenSpec records, attestations, evidence, or command JSON

### Requirement: Product Core Adopter Isolation

ETHOS SHALL keep adopter-specific domain names out of product Python code.

#### Scenario: Product code is scanned

- **WHEN** architecture tests scan package source files
- **THEN** adopter names are absent from semantic product implementation code

### Requirement: Semantic identity is schema-versioned and runtime-independent

Each supported carrier SHALL use one immutable schema-version protocol.
Identity-bearing defaults, normalization, canonical projection and digest domain
SHALL agree across source, wheels, package runtimes, hosts and processes. Owners
SHALL validate collection members before normalization; input order SHALL NOT
determine validity or identity.

#### Scenario: The same v2 carrier is interpreted in several runtimes

- **WHEN** exact bytes are loaded from the same Git tree
- **THEN** every runtime produces the same semantic identity
- **AND** a changed interpreter requires a new schema version

#### Scenario: A current v1 carrier is encountered after cutover

- **WHEN** normal plan compilation or mutation loads it
- **THEN** ETHOS blocks before deriving current semantic authority
- **AND** only runtime activation's staged state transition may migrate the
  previous Lease relation

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

## ADDED Requirements

### Requirement: Durable event-like values are consumed Attestations

ETHOS SHALL retain a durable event-like value only as an Attestation consumed by
a current evaluator or derived projection. Declaration-only streams, generic
event logs, Campaign state, mutable inbox state, and Chronicle authority SHALL
be absent.

#### Scenario: Tracked declarations are loaded

- **WHEN** ETHOS loads its tracked declarations
- **THEN** they contain only currently consumed policies
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

#### Scenario: A durable governance decision is one Attestation

- **WHEN** a governance decision becomes durable
- **THEN** it is one Attestation v2 in the sole set, not Chronicle
- **AND** no campaign CEL, event table, migration ledger, acknowledgement,
  consumed flag, or inbox cursor is created

## REMOVED Requirements

### Requirement: Physical Target Product Homes

**Reason**: The separate target packages collapsed into the one `src/ethos` wheel (`bd3a707e3`), and the test that audited their package metadata and READMEs was removed (`e956eb43c`). The PDC (481) gives physical shape to the Module Layout Rules.

**Migration**: Physical shape is governed by `rules/module-layout.md`, and the layer contract by `.config/checks/import-linter/import-linter.toml`.

### Requirement: Event entities require an executable dataflow

**Reason**: Two of its scenarios named retired carriers: a lifecycle declaration (`system/lifecycle.toml`, deleted in `8b53af332`) and "Chronicle remains authoritative evidence", whose body already said the opposite. OpenSpec keeps scenario names across a modification.

**Migration**: Replaced by the requirement "Durable event-like values are consumed Attestations", which keeps the same obligation and the current scenarios.
