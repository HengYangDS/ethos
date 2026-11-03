## ADDED Requirements

### Requirement: Hosted uv setup installs the Mise-declared uv

ETHOS's hosted projections SHALL install the uv version that the repository's Mise configuration
declares, read from that configuration when the projections are compiled. The CI model SHALL NOT
name a uv version.

#### Scenario: The Mise configuration declares another uv

- **WHEN** the Mise configuration's uv version changes and the projections are compiled
- **THEN** every hosted uv setup step installs that version
- **AND** the CI model needs no edit
