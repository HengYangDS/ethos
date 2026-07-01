# ETHOS Quality

## Purpose

ETHOS SHALL define quality, determinism, documentation quality, proof policy,
and asset-governance semantics as a first-class product family.

## Requirements

### Requirement: Quality Asset Model

ETHOS SHALL model repository assets across code, docs, shell, configuration,
evidence, release artifacts, and adopter profiles.

#### Scenario: Asset policy is reported

- **WHEN** `ethos quality asset-policy --json` runs
- **THEN** ETHOS reports asset classes, dimensions, and mature tool adapter
  profiles without executing provider tools

### Requirement: Gate Descriptor Model

ETHOS SHALL describe quality gates with asset classes, dimensions, execution
mode, evidence class, trust-bearing classification, tool adapter, file-write
policy, network policy, and version source.

#### Scenario: Gate descriptors are reported

- **WHEN** `ethos quality gates --json` runs
- **THEN** every gate includes the quality descriptor fields required by the
  gate schema

### Requirement: Proof Policy Lattice

ETHOS SHALL distinguish planned, readiness, executed, proven, blocked,
accepted-risk, and waived-nonblocking proof states.

#### Scenario: Trust-bearing consumers require proven evidence

- **WHEN** `ethos quality proof-policy --json` runs
- **THEN** only `proven` is marked trust-bearing for claim, land, publish,
  release, and self-governance consumers

### Requirement: Documentation Quality Profile

ETHOS SHALL make documentation faithfulness, expressiveness, and elegance
mechanically checkable through metadata, visible reader sections, glossary,
links, anchors, and command examples.

#### Scenario: Docs profile is reported

- **WHEN** `ethos quality docs --json` runs
- **THEN** ETHOS reports docs quality profile checks alongside current docs
  registry health
