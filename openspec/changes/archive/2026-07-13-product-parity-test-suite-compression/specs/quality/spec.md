## ADDED Requirements

### Requirement: Declarative Product-Parity Test Partitions

ETHOS SHALL represent finite, uniform product-parity verification partitions as
declarative pytest case tables and SHALL centralize repeated inert test payload
and evidence-file setup when the resulting scoped representation is smaller.

#### Scenario: Accepted differences retain exact contracts

- **WHEN** a case covers an external stricter state, gap, or plan scope
- **THEN** the table asserts the same semantic-diff and accepted-difference
  contract with a domain-named case identifier

#### Scenario: Compression preserves diagnostic boundaries

- **WHEN** product-parity tests are consolidated
- **THEN** false-negative, process-failure, schema-validation, and integration
  boundaries remain independently named and the recorded surface is smaller
