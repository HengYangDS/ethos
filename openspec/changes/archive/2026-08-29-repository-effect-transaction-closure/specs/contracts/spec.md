## REMOVED Requirements

### Requirement: Commitment v2 identity is explicit and bounded

**Reason**: The v2 schema persisted authored intent, lineage, research state, and
ordering constraints that official OpenSpec and fresh repository facts already
own.

**Migration**: Compile the minimal transient Commitment described by the
repository-transaction capability and retain no v2 carrier or compatibility
reader.

## MODIFIED Requirements

### Requirement: Attestation v2 payload and relations are open and composable

Attestation v2 SHALL bind an open predicate, `{kind, body}` payload, canonical
relations, evidence, validity, closed verdict, exact digests, and
`mints_authority=false`. Relations SHALL sort by kind, target kind, target id,
and canonical attributes and SHALL reject duplicate values and duplicate
relation identity keys. Every field SHALL be explicit; nullable digest and
validity bindings SHALL project as `null`; advisories and evidence refs SHALL be
sorted unique strings. Payload bodies and relation attributes SHALL obey the
closed canonical JSON value grammar. At least one evidence reference, exact
digest binding, or relation SHALL be present.

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
Commitment, Change, acceptance set, or task graph.

#### Scenario: Feedback arrives outside the active Commitment

- **WHEN** it is relevant but not already required by the bounded Change
- **THEN** its selection remains available to a future official OpenSpec Change
- **AND** current effect authority remains unchanged
