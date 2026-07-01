## ADDED Requirements

### Requirement: Retired Family Command Vocabulary
ETHOS SHALL reject retired family-style command prefixes from current docs.

#### Scenario: Retired family command appears
- **WHEN** current docs contain `ethos governance`, `ethos workspace`,
  `ethos agent`, `ethos project`, `ethos kernel`, or `ethos node` as a command
- **THEN** `ethos quality command-registry --json` reports a required gap
