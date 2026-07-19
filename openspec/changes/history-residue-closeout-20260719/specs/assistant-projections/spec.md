## ADDED Requirements

### Requirement: Terminal assistant projections are derived, not root configuration

ETHOS SHALL derive assistant and host projections from repository source,
activation registries, declared surfaces, and schemas, and SHALL NOT require or
scaffold a root `.ethos/assistants.toml` truth file.

#### Scenario: A repository is scaffolded or parity-checked

- **WHEN** ETHOS renders the current adopter scaffold or checks its manifest
- **THEN** `.ethos/assistants.toml` is absent from required artifacts
- **AND** assistant projection behavior continues to come from canonical source
  and activation contracts.

#### Scenario: The product removes the retired projection file

- **WHEN** the product checkout no longer contains `.ethos/assistants.toml`
- **THEN** projection checks and assistant tests remain valid
- **AND** no runtime consumer treats the removed file as required truth.
