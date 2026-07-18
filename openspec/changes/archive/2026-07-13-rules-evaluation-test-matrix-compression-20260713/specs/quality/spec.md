## ADDED Requirements

### Requirement: Compact Declarative Rules-Evaluation Test Inputs

ETHOS SHALL represent stable rule-evaluation fact envelopes through compact
immutable test declarations and SHALL remove equivalent coverage-only scenario
bodies when the canonical test surface preserves their public contracts.

#### Scenario: Fact and waiver partitions remain fail-closed

- **WHEN** the rules test suite evaluates malformed, unavailable, stale,
  non-deterministic, conflicting, or waived facts
- **THEN** the canonical tests assert the same public state and required-gap
  contract while duplicate coverage-only scenario bodies are absent

#### Scenario: Compression does not weaken verification

- **WHEN** compact fact declarations replace legacy test setup
- **THEN** focused coverage and the repository proof floor still pass and the
  targeted effective test-line total is lower than its recorded baseline
