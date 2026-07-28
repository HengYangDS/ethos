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
