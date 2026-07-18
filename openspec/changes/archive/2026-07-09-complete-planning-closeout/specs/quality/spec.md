## ADDED Requirements

### Requirement: Completed tooling baseline remains evidence-bound

ETHOS SHALL distinguish completed active tooling gates from planned or optional
adapter work by requiring owner surfaces, proof coverage, and claim evidence
before a roadmap item is treated as current product truth.

#### Scenario: Closeout manifest binds the completed baseline

- **WHEN** the tooling adoption closeout is reviewed
- **THEN** the closeout evidence manifest SHALL hash the active claim, chronicle,
  and complete closeout OpenSpec carrier
- **AND** active gates SHALL have tool catalog entries, config owners, reusable
  runners or ETHOS command surfaces, CI or hook projections, and tests or proof
  coverage
- **AND** planned adapters SHALL NOT appear as active quality-floor gates until a
  later accepted change proves those owner surfaces.
