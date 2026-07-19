## ADDED Requirements

### Requirement: Event entities require an executable dataflow

ETHOS SHALL retain an event entity only when a tracked production path creates
it and a tracked consumer, reducer, or evidence boundary uses it. Declaration-
only streams and unused local event logs SHALL be absent.

#### Scenario: workflow contract is loaded

- **WHEN** the workflow declaration is validated and projected
- **THEN** it SHALL contain only executable transitions, handoffs, commitments,
  practice changes, and runtime projections
- **AND** no event model, event count, or event-locality rule without a producer
  and consumer SHALL be emitted.

#### Scenario: local state is initialized

- **WHEN** ETHOS initializes ignored local SQLite state
- **THEN** it SHALL create only tables consumed by current product behavior
- **AND** unused generic event and chronicle-event tables and CRUD APIs SHALL be absent.

#### Scenario: Chronicle remains authoritative evidence

- **WHEN** a governance decision becomes durable
- **THEN** its Chronicle evidence SHALL remain governed by repository evidence contracts
- **AND** removing unused SQLite event logs SHALL NOT create a parallel event bus or truth store.
