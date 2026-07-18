## ADDED Requirements

### Requirement: Optional tool adapters remain replaceable

ETHOS SHALL expose optional adapter boundaries for environment runners, graph
systems, task ledgers, and agent method packs without making them product
substrate.

#### Scenario: Adapter profile is reported

- **WHEN** `ethos quality tool-profiles --json` reports tool adapters
- **THEN** Nox, Pixi, Pants, task-ledger, and agent-method-pack entries SHALL be
  visible as adapter-only boundaries
- **AND** their output SHALL NOT replace ETHOS proof, OpenSpec lifecycle checks,
  claims, evidence, or Git-native Work Lane semantics.
