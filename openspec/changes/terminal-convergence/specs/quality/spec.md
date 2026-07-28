## MODIFIED Requirements

### Requirement: One Owner Per Property
Each quality property SHALL have one admitted owner consumed identically by local and hosted execution.

#### Scenario: Two tools claim the same property

- **WHEN** the tracked tool, gate, and owner-script declarations are audited
- **THEN** the overlap is a required gap unless one tool is explicitly a bounded
  pilot replacing the other
- **AND** a baseline, hosted dashboard, or convenience wrapper cannot become a
  second authority

#### Scenario: duplicate quality implementations exist
- **WHEN** two owners claim the same quality property
- **THEN** admission blocks until one owner is selected and the other is removed

### Requirement: Warning And Suppression Zero
Warnings, suppressions, stale projections, and unknown required facts SHALL fail closed; no passing verdict coexists with them.

#### Scenario: A command succeeds with a warning

- **WHEN** a governed quality command exits zero but emits an unapproved warning
- **THEN** its gate fails
- **AND** the warning must be removed or represented by an explicit bounded
  decision with a deletion condition

#### Scenario: Production contains a suppression

- **WHEN** quality proof finds `fmt off/on`, `noqa`, type-ignore, coverage-ignore,
  or an equivalent suppression in production source
- **THEN** proof blocks until the construct is deleted or replaced by a truthful
  semantic layout

#### Scenario: a CI warning is emitted
- **WHEN** a required quality command emits a warning
- **THEN** the quality verdict blocks rather than reporting pass

### Requirement: Native Carrier Quality
Quality SHALL preserve each carrier's native syntax and owner rather than mechanically rewriting prose or inventing a universal format.

#### Scenario: A carrier is checked

- **WHEN** config, docs, shell, or format proof runs
- **THEN** deterministic format, syntax, schema, links, anchors, and shell safety
  are checked by the declared native owner
- **AND** the gate does not rewrite governed content during proof

#### Scenario: a generated artifact drifts
- **WHEN** a declared projection differs from its source binding
- **THEN** the owning drift check blocks the stale artifact
