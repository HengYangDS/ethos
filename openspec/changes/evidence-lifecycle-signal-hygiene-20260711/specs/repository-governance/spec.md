## ADDED Requirements

### Requirement: Claim evidence freshness is explicit

ETHOS SHALL distinguish durable historical support from evidence that asserts
current repository state. Every active claim SHALL declare exactly one evidence
freshness mode: `historical`, `head_bound`, or `semantic_scope`.

#### Scenario: historical evidence is durable without pretending currentness

- **WHEN** an active claim declares `historical` freshness
- **THEN** ETHOS verifies its dated evidence digest and all ordinary active-claim
  trust-envelope requirements
- **AND** it does not emit a missing-HEAD migration advisory
- **AND** it does not claim that the historical evidence proves the current HEAD.

#### Scenario: currentness-sensitive evidence fails closed

- **WHEN** an active claim declares `head_bound` or `semantic_scope` freshness
- **THEN** ETHOS requires the binding fields of that mode
- **AND** a different declared HEAD blocks `head_bound` evidence
- **AND** a changed declared semantic target blocks `semantic_scope` evidence
- **AND** absent or unknown freshness mode is a required gap.
