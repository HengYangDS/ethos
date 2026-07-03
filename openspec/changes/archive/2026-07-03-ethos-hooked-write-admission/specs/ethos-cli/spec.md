## ADDED Requirements

### Requirement: Hook Admission Command

ETHOS CLI SHALL expose hook admission through a maintainer/reference command
without expanding the five-command public workflow.

#### Scenario: Hook admission command returns product JSON

- **WHEN** `ethos hook admit pre-tool <path> --editor-root <root>
  --require-editor-root --json` runs
- **THEN** the result command is `hook admit`
- **AND** the result state is `admitted`, `blocked`, or `fused`
- **AND** the payload includes layer, target root, checkout role, decision, and
  required gaps.

#### Scenario: Hook command remains a reference surface

- **WHEN** `ethos quality command-registry --json` reports command surfaces
- **THEN** `ethos hook` is a maintainer/reference command
- **AND** it is not counted as a public workflow command.
