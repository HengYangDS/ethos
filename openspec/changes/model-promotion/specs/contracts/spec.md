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
Strings and keys SHALL be Unicode scalar values preserved without normalization;
identifiers SHALL use lowercase ASCII colon-separated segments; timestamps SHALL
use the strict canonical RFC 3339 UTC form; canonical JSON SHALL use RFC 8785
string escaping and UTF-16 key ordering with UTF-8 output, unique object keys,
no insignificant whitespace, and only null, booleans, strings, I-JSON safe
integers, arrays, and objects. Floats, duplicate object keys, lone surrogates,
noncanonical member bytes, and implicit Unicode normalization SHALL be invalid.

String sets SHALL sort by canonical JSON bytes; digest sets SHALL sort
lexicographically. Carrier sets already SHALL be in that order rather than
silently normalized. Dependencies SHALL be `{kind,target,attributes}`;
hypotheses SHALL be `{id,kind,body}`; falsifiers SHALL be
`{id,hypothesis_id,kind,body}`; experiment protocols SHALL be
`{id,hypothesis_ids,kind,body}`. Every nested field SHALL be required, open
`body` and `attributes` values SHALL use the same canonical JSON grammar, and
their declared tuple keys SHALL determine deterministic ordering and duplicate
rejection.

#### Scenario: A v2 Commitment is loaded

- **WHEN** carrier bytes omit an identity field, contain a duplicate, use a
  context-dependent subject alias, or fail a typed value contract
- **THEN** validation blocks before a semantic digest is produced

#### Scenario: Equivalent runtime values are projected

- **WHEN** source, wheel, and package-only runtimes load the same valid v2 bytes
- **THEN** they produce byte-identical canonical JSON and the same
  `ethos.commitment.v2` domain-separated digest
- **AND** a float, lone surrogate, duplicate key, non-canonical time,
  out-of-range integer, or unsorted set is rejected rather than normalized
  silently

#### Scenario: Selected intent becomes normative

- **WHEN** input is accepted for implementation
- **THEN** a successor Commitment binds predecessor and selection identities
- **AND** the predecessor Change is not silently expanded

### Requirement: Attestation v2 payload and relations are open and composable

Attestation v2 SHALL bind an open predicate, `{kind, body}` payload, canonical
relations, evidence, validity, closed verdict, exact digests, and
`mints_authority=false`. Relations SHALL sort by kind, target kind, target id,
and canonical attributes and SHALL reject duplicate values and duplicate
relation identity keys. Every field SHALL be explicit; nullable digest and
validity bindings SHALL project as `null`; advisories and evidence refs SHALL be
sorted unique strings. Payload bodies and relation attributes SHALL obey the
same closed canonical JSON value grammar as Commitment v2. At least one evidence
reference, exact digest binding, or relation SHALL be present.

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
