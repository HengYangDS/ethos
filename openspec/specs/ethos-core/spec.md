# ETHOS Core

## Purpose

ETHOS SHALL model repository operation through JudgmentSource, Subject,
Commitment, Change, Evidence, Claim, and Chronicle.
## Requirements
### Requirement: Kernel Chain
ETHOS SHALL model repository operation through the kernel chain
JudgmentSource, Subject, Commitment, Change, Evidence, Claim, and Chronicle.
The chain SHALL preserve the compact root philosophy as a generative constraint:
hidden authority and small drift detection, one kernel with discriminated
boundaries, visible and domain-fit measures, and boundary-preserving growth.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through kernel objects without
  depending on repository, assistant, adapter, adopter, or hosted-runner
  packages
- **AND** Claim binds evidence rather than owning lifecycle state
- **AND** semantic claims require a semantic verifier

#### Scenario: Root philosophy constrains future projections
- **WHEN** ETHOS adds a command surface, assistant projection, local model,
  adapter, profile, tool framework, or proof host
- **THEN** the new surface is derived from the existing kernel chain rather than
  becoming a new truth center
- **AND** the surface declares its authority, subject, boundary, evidence, and projection role before promotion

### Requirement: Kernel Result Contract
ETHOS SHALL emit stable JSON result envelopes with `ok`, `summary`,
`diagnostics`, `required_gaps`, `next_actions`, and `data`.

#### Scenario: Automation reads command output
- **WHEN** an automation consumer requests JSON output from an ETHOS command
- **THEN** the response is one parseable object with the stable result fields

### Requirement: Deterministic Action Graph
ETHOS SHALL serialize action graphs deterministically, including validation gaps
for invalid graphs.

#### Scenario: Proof readiness is planned
- **WHEN** ETHOS plans or runs proof gates
- **THEN** selected gates are represented as ordered action graph nodes with
  explicit dependencies and validation gaps

### Requirement: Physical Target Product Homes
ETHOS SHALL provide buildable target product package homes for core,
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
