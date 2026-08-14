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
