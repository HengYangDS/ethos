## ADDED Requirements

### Requirement: Declarative Coordination-Lifecycle Test Partitions

ETHOS SHALL represent finite uniform coordination-lifecycle test inputs as
literal declarative partitions when the formatted scoped test representation is
a net deletion and preserves exact public lifecycle contracts.

#### Scenario: Pure helper cases remain direct and bounded

- **WHEN** handoff context, lease projection, or prewrite normalization cases
  differ only in literal input and expected public output
- **THEN** the test MAY use a local literal case table without deriving expected
  lifecycle semantics from production code

#### Scenario: Effect boundaries retain named coverage

- **WHEN** a case executes handoff, SQLite lease, Git-ref, or recovery effects
- **THEN** the test SHALL retain a domain-named boundary and exact failure or
  state assertion rather than merge unrelated effect sequences

#### Scenario: Duplicate normalization probes are removed safely

- **WHEN** multiple unrelated tests repeat the same shared normalizer scalar
  rejection probe
- **THEN** one direct named normalizer test SHALL retain the tuple and scalar
  contracts and the unrelated duplicate probes SHALL be absent

#### Scenario: Formatter-aware compression is measured

- **WHEN** Python test compression changes a file with pre-existing formatter
  drift
- **THEN** the recorded result SHALL compare the formatter-clean scoped ELOC to
  the formatter-clean baseline and SHALL not claim deletion from unformatted
  layout alone
