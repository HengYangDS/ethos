## ADDED Requirements

### Requirement: Repository semantic ownership is closed

ETHOS SHALL mechanically derive a finite semantic relation from current native
repository carriers and SHALL require every governed semantic identity to have
exactly one current owner and a complete producer, consumer, and selector
relation. The evaluation SHALL preserve provenance until it has classified all
missing, duplicate, orphan, superseded, conflicting, and unknown relations.

#### Scenario: A semantic identity has two current owners

- **WHEN** two current native declarations claim the same governed identity
- **THEN** repository audit reports a duplicate-owner gap naming both sources
- **AND** set deduplication does not hide the conflict

#### Scenario: A required relation is incomplete

- **WHEN** a current producer, consumer, or selector lacks its required
  counterpart
- **THEN** repository audit reports the precise orphan or missing relation
- **AND** the aggregate verdict is not `pass`

#### Scenario: Historical material mentions a retired identity

- **WHEN** an archived Change, evidence record, generated artifact, example, or
  superseded document contains an old identity
- **THEN** it is not admitted as a current owner or consumer
- **AND** exclusion follows structural carrier state rather than a literal
  exception list

#### Scenario: A current specification prohibits a retired command

- **WHEN** an OpenSpec scenario names a retired command only as the object of a
  prohibition or rejection rule
- **THEN** repository audit does not classify that command as a current consumer
- **AND** positive GIVEN or WHEN command subjects remain observable consumers

#### Scenario: A selected carrier cannot be parsed

- **WHEN** a current selected Markdown, TOML, JSON, YAML, or Python carrier
  cannot be parsed by its native parser
- **THEN** repository audit reports that exact carrier as `unknown`
- **AND** the parse failure cannot collapse into an empty passing observation
