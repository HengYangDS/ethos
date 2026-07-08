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

### Requirement: Published Distribution Boundary
Distribution manifests SHALL publish only neutral launcher assets and SHALL NOT
ship historical evidence, host-local state, tests, adopter-private records, or
person attribution metadata as product defaults.

#### Scenario: npm package scope is allowlisted
- **WHEN** `ethos quality product-boundary --json` audits distribution manifests
- **THEN** the root workspace package is non-publishable
- **AND** the npm distribution manifest declares an explicit `files` allowlist
- **AND** that allowlist is limited to launcher assets and neutral package docs
- **AND** author, authors, maintainers, and contributors metadata are absent

### Requirement: Distribution Adapter Outside Python Packages
ETHOS SHALL keep npm launcher metadata under `distributions/npm` and outside
the Python package workspace.

#### Scenario: npm launcher is checked
- **WHEN** npm workspace metadata is inspected
- **THEN** it references `distributions/npm`
- **AND** it does not reference `packages/ethos-node`
- **AND** the launcher forwards to the Python ETHOS command plane
