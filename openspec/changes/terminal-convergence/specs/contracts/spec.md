## ADDED Requirements

### Requirement: Language-neutral Terminal Contracts
ChangeContract, Attestation, RepositoryFacts, PlanIR, permission, adapter, and pack contracts MUST have language-neutral schemas and strict Python bindings without duplicate model owners.

#### Scenario: A non-Python adopter consumes a plan
- **WHEN** it validates a PlanIR instance against the published schema
- **THEN** it can interpret node identity, dependencies, verdicts, permissions, and artifact references without importing Python code

### Requirement: Singular Typed Attestation Algebra
Under the kernel capability's `Minimal Semantic Kernel` requirement, Attestation
SHALL remain one content-addressed persistent envelope with exactly six typed
variants: `observation`, `judgment`, `proof`, `effect`, `external-assurance`, and
`amendment`. The variants SHALL enforce their own content and binding invariants
without separate stores, schemas, ledgers, or lifecycle entities.

#### Scenario: A producer issues a proof
- **WHEN** it issues `Attestation(kind = "proof")`
- **THEN** the envelope binds the selected ChangeContract digest, exact HEAD and
  tree, gate identifiers, verifier boundary, and evidence references

#### Scenario: New evidence meaning does not fit a variant
- **WHEN** either valid meaning would be lost or coerced
- **THEN** schema emission and evidence retirement block
- **AND** the conflict invokes [Model Promotion](../../../../../docs/governance/product-design-contract.md#model-promotion)
  while preserving both evidence scenarios

### Requirement: Proposition Verification And Historical Projection
A verifier-bounded proposition MUST exist only as a proposition inside a ChangeContract or Attestation
and MUST be limited by its named verifier, evidence, scope, and validity boundary.
A historical projection MUST be a derived historical projection over Git, OpenSpec archives,
and Attestations. Neither term MAY own a model, schema, root, store, current truth,
or lifecycle.

#### Scenario: A verifier cannot establish a proposition
- **WHEN** a ChangeContract or Attestation contains a proposition outside the
  verifier's declared boundary
- **THEN** strict validation rejects the proposition
- **AND** no verifier-bounded proposition entity, verifier-bounded proposition store, or derived historical projection store is created to carry it

### Requirement: Vendor-neutral Actor Reference
Actor references MUST use the opaque four-segment form `kind:namespace:instance-kind:id`; the kernel MUST validate structure and equality only and MUST NOT enumerate vendors or infer privilege from names.

#### Scenario: A new agent vendor participates
- **WHEN** it supplies a structurally valid actor reference and explicit permissions
- **THEN** the same lifecycle and authority checks apply without a kernel code change

### Requirement: Immutable Intent Amendment
A ChangeContract MUST remain immutable. The admitted amendment set is empty in
this release. A later resolver MAY derive effective intent only by folding
Git-reachable, authority-admitted, ordered, digest-chained amendment
Attestations, without a Lease wire change.

#### Scenario: A later release resolves admitted amendments
- **WHEN** another actor takes over with the base contract and admitted amendment
  Attestations
- **THEN** it reconstructs the same effective intent without the original
  transcript or a Lease migration

### Requirement: Base And Effective Contract Identity
The immutable base ChangeContract digest MUST identify intent lineage. The
admitted amendment set is empty in this release, so the effective
ChangeContract and every generic `contract_digest` or
`change_contract_digest` MUST equal the selected base digest. A later resolver
MAY fold only Git-reachable, authority-admitted, digest-chained amendment
Attestations without changing or migrating the Lease wire.

#### Scenario: Current release resolves a Worktree Family
- **WHEN** a Worktree Family selects its ChangeContract
- **THEN** its Lease base digest, PlanIR contract digest, and proof or effect
  Attestation ChangeContract digest are exactly equal
- **AND** no active amendment, fallback, alias, or parallel intent identity is
  admitted

#### Scenario: A parallel intent identity is presented
- **WHEN** a Lease or current lifecycle reader supplies
  `effective_contract_digest` or another parallel intent identity
- **THEN** strict validation rejects it rather than aliasing, dual-reading, or
  falling back from ChangeContract identity

### Requirement: Singular Active Change Carrier
Each active OpenSpec Change MUST use `contract.toml` as the sole ETHOS-owned
carrier for repository subject, intent, and material scope. verifier-bounded proposition and derived historical projection
MUST NOT be modeled as entities or stores, and `scope.toml` MUST NOT participate
in the current lifecycle verdict.

Protected release, accepted, and candidate roots MUST contain no active Change
carrier. A Work Lane started for an existing intent MUST materialize its sole
active carrier from one explicitly selected source Work Lane into the destination
initialization commit; the Lease and PlanIR MUST bind that final HEAD and the
same base ChangeContract digest.

#### Scenario: A material path is evaluated
- **WHEN** `lane prewrite`, changed planning, or proof selects an active Change
- **THEN** all three surfaces evaluate the same strict `ChangeContract.scope`
- **AND** malformed or historical parallel carriers grant no authority

#### Scenario: Intent is promoted into a new Work Lane
- **WHEN** lane start selects a source Work Lane and clean candidate base
- **THEN** the destination initialization commit contains exactly the selected
  active carrier and no candidate-root active residue
- **AND** source HEAD, destination HEAD, Lease base digest, and PlanIR contract
  digest are explicit and deterministic

### Requirement: Lifecycle Declaration Contract
The lifecycle declaration MUST expose only transition policy, lease transition,
and PlanIR action sections. It MUST reject derived terminal program, model refinement, runtime,
evaluation, and run-state sections.

#### Scenario: A parallel runtime section is supplied
- **WHEN** the lifecycle declaration contains a runtime or run-state field
- **THEN** strict contract and JSON Schema validation reject it before projection

#### Scenario: A campaign section is supplied
- **WHEN** the lifecycle declaration contains derived terminal program state, policy, or CEL
- **THEN** strict validation rejects the parallel lifecycle owner
- **AND** terminal program state is compiled as `(ChangeContract,
  RepositoryFacts, prior Attestations) -> PlanIR -> new Attestations`

### Requirement: Terminal Contract Compilation And Evidence

The contracts capability SHALL preserve the migrated operational boundaries while using ChangeContract and Attestation as its only persistent semantic entities. Fresh RepositoryFacts and prior Attestations SHALL compile a transient PlanIR; new Attestations SHALL record verifier-bounded outcomes, and historical views SHALL remain derived projections.

#### Scenario: Promotion target is validated
- **WHEN** ETHOS validates a ChangeContract-selected target
- **THEN** the target kind is one of source, tests, docs, schema, openspec, or
  evidence
- **AND** the target path is repository-relative

#### Scenario: Trust envelope is emitted

- **WHEN** ETHOS reports verifier-bounded proposition governance
- **THEN** each Attestation binds the selected ChangeContract digest, verifier,
  scope, validity boundary, evidence references, verdict, and required gaps
- **AND** no fallback, compatibility, or parallel ownership field is emitted.

### Requirement: Spec-only Capability Identity And Proposal Intent

`openspec/specs/<capability>/spec.md` SHALL be the sole accepted capability
identity and requirements carrier. An OpenSpec carrier is not a truth owner;
deltas own changed behavior, `system/gates.toml` owns gate selection, and the
ChangeContract owns acceptance. Proposal intent is exactly `subject`, `reuse`,
and `change`.

#### Scenario: A proposal names an accepted capability

- **WHEN** ETHOS validates the active proposal
- **THEN** the named `spec.md` establishes identity and `subject`, `reuse`, and
  `change` are required without another file or inferred field

#### Scenario: Legacy facet metadata is rejected

- **WHEN** a proposal supplies `facet:lifecycle`, `facet:surface`,
  `facet:authority`, or any other metadata key
- **THEN** ETHOS reports a required unknown-metadata gap without ignore, alias,
  inference, or fallback behavior

## MODIFIED Requirements

### Requirement: Governed Repository Context Contract
`governance_context` SHALL be a derived command projection over the selected
ChangeContract, fresh RepositoryFacts, and prior Attestations. It SHALL NOT own a
kernel chain, command registry, or lifecycle state.

#### Scenario: Governance context is emitted
- **WHEN** a public command returns repository context
- **THEN** it identifies the repository, profile, six public roots, and adapter
  boundary without becoming reusable authority

#### Scenario: Governance context is provider-neutral
- **WHEN** ETHOS emits `governance_context`
- **THEN** the context identifies the subject as a repository
- **AND** the context records the profile, kernel
  chain, and singular lifecycle command semantics
- **AND** `shared_commands` and `transition_commands` contain the five transition
  commands
- **AND** `reader_projection_commands` contains `ethos status`
- **AND** provider, host, editor, model, and toolchain choices remain outside
  product semantics

### Requirement: PlanIR Transition Contract
ETHOS SHALL compile `(ChangeContract, RepositoryFacts, prior Attestations) ->
PlanIR -> new Attestations` through one lifecycle declaration for
repository-semantic outcomes. Routine local coordination and its postcondition
receipts SHALL remain ignored local state rather than Attestations. A parallel
run-state read model, event stream, or orchestration store SHALL NOT own lifecycle
truth.

#### Scenario: A transition plan is inspected
- **WHEN** ETHOS compiles a governed change
- **THEN** PlanIR exposes ordered checks, judgment Attestations, guarded effects,
  permissions, and a closed verdict
- **AND** every dependency is acyclic and every effect is permission-bounded

### Requirement: Handoff Package Contract
A handoff package SHALL remain a digest-bound context projection that names the
source Lease `base_change_contract_digest`, source refs, prior Attestations,
freshness, and target actor. Its content becomes repository truth only when incorporated into a
selected ChangeContract or Attestation; Chronicle may derive history afterward
but cannot receive a direct promotion from the handoff package.

#### Scenario: A handoff package is validated
- **WHEN** source digests or required Attestations are stale
- **THEN** takeover blocks until current RepositoryFacts can reconstruct the
  selected ChangeContract context

#### Scenario: Handoff package is validated
- **WHEN** a handoff package is inspected
- **THEN** it records source refs, source digests, the exact source Lease base
  ChangeContract digest, target actor, intended use,
  freshness state, and proof or evidence refs
- **AND** stale source digests block trust-bearing handoff propositions
- **AND** handoff content remains context until incorporated into a selected
  ChangeContract or Attestation
- **AND** Chronicle is only subsequently derived from admitted truth; the
  handoff package is not directly promoted into truth

### Requirement: Skill Package Manifest
ETHOS SHALL bind each provider-visible skill package to a content-addressed
manifest that declares its entrypoint, included files, digest algorithm,
required sections, quality rules, and capability classes. Manifest validation
SHALL be consumed by the admitted `playbooks-v2` gate rather than a standalone
command product.

#### Scenario: package digest mismatch is detected
- **GIVEN** a skill package manifest declares included files and an expected
  digest
- **WHEN** `ethos prove --gate playbooks-v2 --json` evaluates the package
- **THEN** proof reports a required package-digest gap when the content differs

#### Scenario: unsafe package paths are rejected
- **GIVEN** a package path, entrypoint, or included file is absolute or escapes
  its allowed root
- **WHEN** the `playbooks-v2` gate validates the manifest
- **THEN** proof reports a required package-path gap without reading outside the
  repository or package directory

#### Scenario: package capabilities are classified
- **GIVEN** a package declares command, protocol, script, or host capabilities
- **WHEN** the `playbooks-v2` gate validates the manifest
- **THEN** read-only capabilities reject mutation, proof capabilities identify
  admitted gate commands, and guarded mutation capabilities declare a guard

### Requirement: Explicit mutation context contract
ETHOS SHALL define mutation-capable operations with explicit target-root,
checkout-role, editor-root, target-path, and admission-result fields.

#### Scenario: Mutation context is auditable
- **WHEN** a mutation-capable operation is admitted or blocked
- **THEN** the machine result includes target root, editor root, branch role,
  target paths, judgment Attestation, and required gaps

## REMOVED Requirements

### Requirement: Capability Profile Contract

**Reason**: The parallel entity duplicates identity, requirements, gates, and acceptance without owning behavior.

**Migration**: `spec.md` owns identity and requirements; proposal intent is only `subject`, `reuse`, and `change`; existing gate and acceptance owners remain.

**Replacement**: Spec-only Capability Identity And Proposal Intent

**Scenario replacement**: Capability profile is inspected -> A proposal names an accepted capability

### Requirement: Capability Profile Facet Contract

**Reason**: Routing facets create a second proposal schema independent of accepted behavior.

**Migration**: Proposal validation accepts only `subject`, `reuse`, and `change` and rejects every additional key.

**Replacement**: Spec-only Capability Identity And Proposal Intent

**Scenario replacement**: Capability profile declares routing facets -> Legacy facet metadata is rejected

### Requirement: Promotion Target Contract

**Reason**: The accepted form assigns durable semantic ownership to a retired model or binds operational truth to that model.

**Migration**: Terminal Contract Compilation And Evidence absorbs every scenario through the selected base ChangeContract, fresh RepositoryFacts, transient PlanIR, and verifier-bounded Attestations; history remains a derived projection.

**Replacement**: Terminal Contract Compilation And Evidence

### Requirement: Trust Envelope Contract

**Reason**: The accepted form assigns durable semantic ownership to a retired model or binds operational truth to that model.

**Migration**: Terminal Contract Compilation And Evidence absorbs every scenario through the selected base ChangeContract, fresh RepositoryFacts, transient PlanIR, and verifier-bounded Attestations; history remains a derived projection.

**Replacement**: Terminal Contract Compilation And Evidence
