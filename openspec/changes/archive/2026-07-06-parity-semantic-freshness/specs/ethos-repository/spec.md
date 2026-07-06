## ADDED Requirements

### Requirement: Parity Evidence Semantic Freshness

ETHOS SHALL bind tracked shadow parity evidence to the parity-relevant semantic
Git tree so evidence commits do not stale themselves and product-semantic
changes still reopen parity gaps.

#### Scenario: evidence commit does not stale its own parity evidence

- **GIVEN** tracked parity evidence records the product head, target head, and
  semantic digest over the parity-relevant path set
- **AND** the repository later commits only the parity evidence itself
- **WHEN** `ethos report --json` evaluates parity gaps
- **THEN** the parity evidence remains fresh by semantic digest
- **AND** the provenance still reports whether the recorded head equals the
  current head

#### Scenario: product semantic change stales parity evidence

- **GIVEN** tracked parity evidence records a previous parity-relevant semantic
  digest
- **WHEN** a later commit changes a parity-relevant path
- **THEN** ETHOS reports a parity evidence freshness gap
