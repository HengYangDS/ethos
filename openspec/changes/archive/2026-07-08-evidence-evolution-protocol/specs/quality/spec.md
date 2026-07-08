## ADDED Requirements

### Requirement: Evidence Freshness Protocol Gate

ETHOS SHALL treat evidence freshness as the read model that checks claim
digests, claim evidence freshness, and evolution-ledger protocol health without
creating another truth store.

#### Scenario: evidence freshness reports claim and evolution protocol health

- **WHEN** `ethos quality evidence-freshness --json` runs
- **THEN** the result includes claim digest/head checks from `evidence/claims`
- **AND** the result includes evolution protocol checks from `evolution/ledger.toml`
- **AND** required gaps from either surface block the command
- **AND** the command does not execute proof refs or claim hosted CI success

#### Scenario: default proof includes evidence freshness

- **WHEN** `ethos prove --json` builds the default product or adopter proof graph
- **THEN** the graph includes the trust-bearing `evidence-freshness` gate after
  `claims`
- **AND** the gate command is `ethos quality evidence-freshness --json`
