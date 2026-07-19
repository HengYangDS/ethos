## ADDED Requirements

### Requirement: Metric-Domain Budget Contract

ETHOS SHALL define repository budgets as versioned measures inside explicit
carrier and scope domains rather than as one convertible cross-language scalar.

#### Scenario: Repository source is measured by native domains

- **WHEN** ETHOS defines Budget Contract v2 metrics
- **THEN** programming source SHALL use language-native lexical tokens and
  normalized syntax or payload bytes
- **AND** structured declarations SHALL use semantic nodes and normalized scalar
  payload bytes
- **AND** templates SHALL separate dynamic structure from static payload
- **AND** tests, evidence, derived projections, documentation, and authored
  product source SHALL remain distinct scopes
- **AND** hard coordinates SHALL combine with logical AND without weighted or
  cross-coordinate compensation.

#### Scenario: Metric semantics are content-addressed

- **WHEN** a carrier is measured
- **THEN** the observation SHALL bind the metric version, parser or lexer,
  parser version, grammar digest, normalization version, aggregation rule,
  carrier rule, repository-relative path, and content identity
- **AND** parser unavailability, invalid input, ambiguous classification, or an
  unsupported governed carrier SHALL produce a required gap rather than zero.

#### Scenario: Agent tokens remain operational

- **WHEN** ETHOS budgets an agent prompt, model context, or generated response
- **THEN** model/tokenizer-specific BPE tokens MAY govern that operational scope
- **AND** those tokens SHALL NOT become repository-source truth or a conversion
  basis for source-budget coordinates.
