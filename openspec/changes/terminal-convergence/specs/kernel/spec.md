## MODIFIED Requirements

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

### Requirement: Minimal Semantic Kernel
Commitment and Attestation are the only persistent semantic entities. Facts is freshly observed context, and TransitionPlan is transient compiled closure. The kernel SHALL keep this boundary.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through the minimal kernel without depending
  on repository, assistant, adapter, adopter, or hosted-runner packages
- **AND** attestations bind evidence without owning reusable authority
- **AND** semantic claims require a current, candidate-external semantic attestation receipt

#### Scenario: semantic attestation remains optional and bounded

- **WHEN** an Attestation declares an independently verified semantic predicate
- **THEN** it SHALL bind a candidate-external receipt to its statement identity,
  evidence digest, semantic scope digest, and exact HEAD
- **AND** the receipt SHALL name an independent reviewer role, basis, pass verdict, validity interval, and `mints_authority = false`
- **AND** missing, malformed, stale, repository-local, or mismatched receipts SHALL block the dependent effect
- **AND** `digest_only` Attestations SHALL require no receipt directory, account,
  daemon, credential, network, or dedicated local account

#### Scenario: a transition is compiled
- **WHEN** ETHOS receives a selected Commitment, fresh Facts, and prior Attestations
- **THEN** it compiles a transient TransitionPlan without persisting a third semantic root

### Requirement: Semantic attestation is receipt-bound and non-authorizing
An Attestation SHALL carry an open predicate, statement, verifier, bindings, validity, and evidence references. Unknown predicates are preserved but non-authorizing.

#### Scenario: Attestation is absent or mismatched

- **WHEN** the Attestation statement or external receipt is missing,
  malformed, stale, repository-local, or does not match a bound fact
- **THEN** ETHOS SHALL block the dependent effect with a machine-readable gap

#### Scenario: Digest-only attestation remains portable

- **WHEN** an Attestation declares `digest_only`
- **THEN** ETHOS SHALL not require or inspect a semantic receipt directory,
  account, daemon, credential, network operation, or dedicated local account

#### Scenario: Digest-only claim remains portable

- **WHEN** a historical or external claim declares `digest_only`
- **THEN** ETHOS SHALL not require or inspect a semantic receipt directory,
  account, daemon, credential, network operation, or dedicated local account

#### Scenario: Semantic attestation has a current semantic scope

- **WHEN** an Attestation declares an independently verified semantic predicate
- **THEN** its evidence freshness mode SHALL be `semantic_scope`
- **AND** its receipt scope and HEAD bindings SHALL match that current scope

#### Scenario: an unfamiliar predicate is received
- **WHEN** an Attestation predicate is syntactically valid but no selected operation understands it
- **THEN** ETHOS preserves and projects it without authorizing an effect

### Requirement: Root Interpretation Boundary
A valid requirement that cannot be represented losslessly by the roots and carrier roles SHALL produce `model_gap`; coercion and retirement block.

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

#### Scenario: a new requirement does not fit the model
- **WHEN** carrier extraction cannot map the requirement without an exception or parallel truth owner
- **THEN** ETHOS preserves the distinction for model promotion and blocks the effect

#### Scenario: processing roles stay owner-local
- **WHEN** a selected operation observes a native, projection, adapter, fact, or
  history carrier
- **THEN** the carrier's narrow owner SHALL classify and validate it without a
  universal registry or parallel read model
- **AND** it SHALL emit a transient descriptor only when a real contextual
  resolution consumer requires one
- **AND** the processing role alone SHALL NOT grant authority
