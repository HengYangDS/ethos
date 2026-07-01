# ETHOS Distribution

## Purpose

ETHOS SHALL expose package-manager launchers without moving command semantics
out of the canonical command plane.

## Requirements

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
- **WHEN** the repository contains a Node distribution adapter under
  `distributions/npm`
- **THEN** uv workspace members list the Python packages explicitly
- **AND** package-manager metadata does not break Python builds

### Requirement: Distribution Adapter Outside Python Packages
ETHOS SHALL keep npm launcher metadata under `distributions/npm` and outside
the Python package workspace.

#### Scenario: npm launcher is checked
- **WHEN** npm workspace metadata is inspected
- **THEN** it references `distributions/npm`
- **AND** it does not reference `packages/ethos-node`
- **AND** the launcher forwards to the Python ETHOS command plane
