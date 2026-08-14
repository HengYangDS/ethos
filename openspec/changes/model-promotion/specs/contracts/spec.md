## MODIFIED Requirements

### Requirement: TransitionPlan Transition Contract

`TransitionPlan` SHALL remain immutable, deterministic, operation-bound derived
IR. Commitment SHALL NOT carry reusable permissions. Stored plan bytes MAY
support exact recovery but SHALL NOT become a semantic root.

#### Scenario: A transition plan is inspected

- **WHEN** ETHOS compiles a governed change
- **THEN** it exposes ordered checks, decisions, effects, exact operation
  authority, and a closed verdict
- **AND** every dependency is acyclic and effect authority is plan-bound

## ADDED Requirements

### Requirement: Commitment v2 identity is explicit and bounded

Commitment v2 SHALL require every identity-bearing field explicitly and compute
a domain-separated digest over its canonical projection. It SHALL include typed
predecessors, selected Attestations, dependencies, hypotheses, falsifiers, and
experiment protocols, and SHALL exclude reusable permissions and mutable state.

#### Scenario: A v2 Commitment is loaded

- **WHEN** carrier bytes omit an identity field, contain a duplicate, use a
  context-dependent subject alias, or fail a typed value contract
- **THEN** validation blocks before a semantic digest is produced

#### Scenario: Selected intent becomes normative

- **WHEN** input is accepted for implementation
- **THEN** a successor Commitment binds predecessor and selection identities
- **AND** the predecessor Change is not silently expanded

### Requirement: Attestation v2 payload and relations are open and composable

Attestation v2 SHALL bind an open predicate, `{kind, body}` payload, canonical
relations, evidence, validity, closed verdict, exact digests, and
`mints_authority=false`. Relations SHALL sort by kind, target kind, target id,
and canonical attributes and SHALL reject duplicates.

#### Scenario: Identical text occurs twice

- **WHEN** it appears at distinct source occurrence coordinates
- **THEN** two Attestations retain distinct identities
- **AND** text digest alone is not occurrence identity

#### Scenario: Known and future relations coexist

- **WHEN** an Attestation carries several known relations and an unknown one
- **THEN** all canonical values round-trip in deterministic order
- **AND** only evaluator-understood relations participate in a verdict

### Requirement: Selection Attestations never mint authority

A selection Attestation SHALL dispose input to a named semantic owner, explicit
absence reason, contradiction, or model gap. It SHALL NOT mutate an active
Commitment, Change, scope, acceptance set, or task graph.

#### Scenario: Feedback arrives outside the active Commitment

- **WHEN** it is relevant but not already required by the bounded Change
- **THEN** its selection remains available to a successor Commitment
- **AND** current effect scope remains unchanged
