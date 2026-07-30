## MODIFIED Requirements

### Requirement: Provider-neutral Contracts
Commitment and Attestation SHALL be the sole portable persistent semantic contracts. Facts and TransitionPlan SHALL be transient inputs and outputs.

#### Scenario: Contracts are inspected
- **WHEN** architecture tests scan `contracts`
- **THEN** contract modules do not import Git, SQLite, subprocess, hosted CI,
  assistant runtime, or adopter-private implementation modules

#### Scenario: a schema is regenerated
- **WHEN** a contract schema is regenerated
- **THEN** it derives from the single semantic model owner rather than a parallel carrier schema

#### Scenario: semantic values cross a contract boundary
- **WHEN** Commitment, Attestation, Facts, or TransitionPlan values are created,
  validated, serialized, or passed to a reducer
- **THEN** nested semantic values are deeply immutable or copied into canonical
  immutable forms
- **AND** equivalent inputs produce byte-stable canonical JSON and the same
  digest without ambient time, process, filesystem, network, or object-identity
  dependence
- **AND** mutation requires a new value rather than changing an existing root

#### Scenario: an Attestation crosses a public boundary
- **WHEN** CLI, SDK, subprocess JSON, or an adapter projects an Attestation
- **THEN** it serializes the canonical open envelope directly
- **AND** caller-selected `kind`, duplicate `content`, `mints_authority`,
  amendment, sequence, or prior-digest compatibility fields are absent

#### Scenario: predicate-owned evidence is issued
- **WHEN** an Attestation records an observation, judgment, proof, or effect
- **THEN** its predicate-owned statement and bindings carry the claim,
  normalized command and result, repository identity, input/output digests,
  exact HEAD, observation time, and freshness boundary required by that predicate
- **AND** contract, scope, source, report, verifier, input, output, HEAD, or
  freshness drift invalidates dependent proof
- **AND** no parallel receipt or proof-record entity owns the same evidence

### Requirement: Governed Repository Context Contract
A Commitment SHALL be immutable identity and intent. Changed scope or intent SHALL create a new Commitment; no amendment chain is a persistent root.

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

#### Scenario: an operator changes intended scope
- **WHEN** intended scope changes
- **THEN** the operator creates a new Commitment and binds the new transition explicitly

### Requirement: TransitionPlan Transition Contract
TransitionPlan SHALL be transient closure over exact Commitment, Facts, prior Attestation, policy, and effect bindings; it SHALL be regenerated whenever an input changes.

#### Scenario: A transition plan is inspected
- **WHEN** ETHOS compiles a governed change
- **THEN** TransitionPlan exposes ordered checks, decisions, effects, permissions, and a closed verdict
- **AND** every dependency is acyclic and every effect is permission-bounded

#### Scenario: an input changes after planning
- **WHEN** any exact input binding changes
- **THEN** the prior TransitionPlan is not reused for an effect

#### Scenario: transition dependencies are compiled
- **WHEN** TransitionPlan orders checks, decisions, and effects
- **THEN** it uses the direct standard-library DAG owner and rejects cycles
- **AND** no graph wrapper, graph registry, or graph database owns transition semantics.

#### Scenario: a transition is evaluated
- **WHEN** the compiler evaluates an exact immutable input set
- **THEN** a pure reducer returns checks, decisions, effects, permissions, and a
  closed verdict without performing I/O or mutating an input
- **AND** only the effect boundary may observe external state or execute an
  admitted exact-CAS effect
- **AND** post-observation and Attestation report the result without feeding
  mutable adapter state back into the reducer

### Requirement: Portable Conformance Surface
The portable contract SHALL be consumable through the public CLI, Python SDK,
subprocess JSON, and optional protocol adapters without duplicating repository
truth or requiring one language, provider, agent host, or carrier layout.

#### Scenario: a non-Python consumer executes a transition
- **WHEN** the consumer uses published language-neutral schemas and subprocess JSON
- **THEN** it observes the same Commitment, Facts, TransitionPlan, verdict, and
  Attestation semantics as the Python SDK
- **AND** protocol-specific fields do not enter the semantic kernel.

#### Scenario: portable interfaces are compared
- **WHEN** the CLI, Python SDK, subprocess JSON, or an optional MCP/A2A-style
  adapter receives the same canonical request
- **THEN** conformance verifies the same schema and protocol version, validation
  and error taxonomy, permissions, deterministic serialization and digest,
  offline behavior, verdict, and semantic result
- **AND** unknown versions, fields, permissions, or required facts fail closed
  without compatibility inference
- **AND** transport metadata, streaming, discovery, authentication, and session
  state remain adapter concerns outside the kernel

#### Scenario: an optional protocol adapter is absent or removed
- **WHEN** no admitted consumer requires MCP, A2A, or another protocol adapter,
  or the adapter is uninstalled
- **THEN** CLI, Python SDK, and subprocess JSON remain complete and conformant
- **AND** removal leaves no catalog, daemon, credential, repository shadow state,
  fallback, or protocol-specific semantic owner
