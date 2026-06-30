# ETHOS Kernel

## Purpose

ETHOS SHALL model repository operation through Constitution, Subject,
Commitment, Change, Evidence, Chronicle, and Evolution.

## Requirements

### Requirement: Public Command Plane
ETHOS SHALL expose one public command plane rooted at `ethos`.

#### Scenario: User-facing operations use ETHOS
- **WHEN** a repository operator runs routine status, planning, proof, landing,
  publishing, quality, or reporting workflows
- **THEN** the documented public entry point is `ethos ...`

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

### Requirement: Evidence And Provenance
ETHOS SHALL project proof-readiness into evidence sets and provenance envelopes
without treating local state as durable evidence.

#### Scenario: Proof evidence is emitted
- **WHEN** ETHOS creates proof evidence
- **THEN** the evidence is HEAD-bound, digest-addressed, and separate from
  ignored local runtime state

### Requirement: Projection Boundary
ETHOS SHALL keep assistant, MCP, ACP, hosted CI, workflow runtimes, external
standards, adoption profiles, and MCP server integration as adapters or thin
projections over repository truth.

#### Scenario: Adapter surfaces are audited
- **WHEN** ETHOS audits product boundaries
- **THEN** adapters do not replace kernel models, schemas, tests, docs, or
  repository source as truth stores

### Requirement: Mutation Authorization
ETHOS SHALL gate apply-mode land and publish readiness on explicit authorization
plus expected HEAD.

#### Scenario: A mutating command is requested
- **WHEN** `ethos land` or `ethos publish` is run in apply mode
- **THEN** ETHOS blocks the mutation unless authorization and expected HEAD are
  both explicit

### Requirement: Governance Quality Gates
ETHOS SHALL expose release, commit signature, schema, gate, command example, and
OpenSpec readiness through governance quality checks.

#### Scenario: Product governance is checked
- **WHEN** ETHOS runs self-audit or proof gates
- **THEN** schema validation, release policy, command registry, evidence, and
  official OpenSpec validation are part of the governance signal

### Requirement: Official OpenSpec Self-Governance
ETHOS SHALL keep `openspec/` as an official self-governance capability for
spec-driven planning and change records while preserving `ethos ...` as the only
public product command plane.

#### Scenario: OpenSpec is present but bounded
- **WHEN** an agent audits ETHOS product surfaces
- **THEN** `openspec/` is present as official governance record storage and is
  not treated as a replacement for ETHOS kernel, command output, schemas,
  tests, or current docs

#### Scenario: OpenSpec official validation is used
- **WHEN** ETHOS audits OpenSpec self-governance
- **THEN** it invokes the official OpenSpec CLI for status and strict validation
  instead of parsing OpenSpec records with ad hoc repository code
