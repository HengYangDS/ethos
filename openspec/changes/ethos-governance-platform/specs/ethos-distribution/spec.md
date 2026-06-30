## ADDED Requirements

### Requirement: Launcher Adapter Boundary
Distribution adapters SHALL forward to the ETHOS command plane and SHALL NOT
define independent governance behavior.

#### Scenario: npm launcher uses command plane
- **WHEN** a user invokes the npm launcher from an ETHOS source checkout
- **THEN** it executes the Python `ethos` command plane through the repository
  environment
- **AND** the Node package remains a launcher-only adapter

### Requirement: Package Manager Isolation
Distribution adapters SHALL be excluded from Python workspace package discovery
unless they are Python packages themselves.

#### Scenario: uv workspace remains Python-only
- **WHEN** the repository contains a Node distribution adapter under `packages/`
- **THEN** uv workspace members list the Python packages explicitly
- **AND** package-manager metadata does not break Python builds
