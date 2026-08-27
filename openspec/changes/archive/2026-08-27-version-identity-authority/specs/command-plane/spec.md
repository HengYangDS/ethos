## ADDED Requirements

### Requirement: Public version inspection exposes immutable provenance
ETHOS SHALL provide one public version inspection path whose human and JSON
projections are derived from the same identity result.

#### Scenario: Human version is requested
- **WHEN** a user runs `ethos --version`
- **THEN** ETHOS prints a concise product and distribution identity
- **AND** it does not serialize a JSON document inside a string.

#### Scenario: Machine version is requested
- **WHEN** an agent runs `ethos --version --json`
- **THEN** stdout is one valid UTF-8 JSON document containing product version,
  distribution version, source commit/tree, wheel SHA256 or explicit absence,
  runtime digest or explicit absence, channel, and acceptance state
- **AND** JSON string escaping is used only where required by JSON syntax.
