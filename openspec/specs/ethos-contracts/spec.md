# ETHOS Contracts

## Purpose

ETHOS SHALL define provider-neutral schemas, result envelopes, adapter
interfaces, policy records, evidence contracts, and command registry contracts
before provider implementations.

## Requirements

### Requirement: Provider-neutral Contracts
ETHOS SHALL keep JSON schemas, TOML config contracts, public result contracts,
attestation envelopes, evidence contracts, and package ontology records free of
provider-specific execution behavior.

#### Scenario: Contracts are inspected
- **WHEN** architecture tests scan `ethos-contracts`
- **THEN** contract modules do not import Git, SQLite, subprocess, hosted CI,
  assistant runtime, or adopter-private implementation modules

### Requirement: Package Ontology Contract
ETHOS SHALL expose the target product package ontology as a machine-readable
contract.

#### Scenario: Package ontology is reported
- **WHEN** `ethos quality package-ontology --json` runs
- **THEN** ETHOS reports target product packages, distribution adapters,
  migration host state, and physical target home readiness from one canonical
  contract

### Requirement: Migration Host Retirement Contract
ETHOS SHALL report active product migration hosts as an empty set when product
topology migration is closed.

#### Scenario: Package ontology is audited after migration closure
- **WHEN** `ethos quality package-ontology --json` runs
- **THEN** `migration_hosts` is empty
- **AND** `migration_status` is `complete`
- **AND** distribution adapters are reported separately from Python packages
