## MODIFIED Requirements

### Requirement: Tool adoption remains profile and adapter scoped

ETHOS SHALL admit mature tooling through contracts, profiles, adapters,
projections, and gates instead of making adopter tools product ontology.

#### Scenario: Planned tools do not become active gates by catalog presence

- **WHEN** a tool is named by a catalog or planned-presence record
- **THEN** that record SHALL NOT make it an active quality gate
- **AND** activation SHALL require a gate in `system/gates.toml` plus its native
  configuration or supply owner
- **AND** the catalog SHALL be deleted rather than retained as parallel state

#### Scenario: Tool admission is positively owned

- **WHEN** a tool participates in a current quality obligation
- **THEN** its active gate SHALL be declared in `system/gates.toml`
- **AND** its native configuration or supply policy SHALL own tool-specific
  behavior and version identity
- **AND** no second tool catalog or planned-presence record SHALL become an
  active quality floor

#### Scenario: Optional method packs remain replaceable

- **WHEN** an agent uses Superpowers or another method pack to plan or review a
  change
- **THEN** the method pack MAY be recorded as execution context
- **AND** repository truth SHALL still require promoted source, docs, OpenSpec,
  claim, evidence, or command proof
- **AND** missing method-pack availability SHALL NOT block ETHOS repository
  governance when equivalent evidence discipline is satisfied
