## ADDED Requirements

### Requirement: Distribution Adapter Outside Python Packages
ETHOS SHALL keep npm launcher metadata under `distributions/npm` and outside
the Python package workspace.

#### Scenario: npm launcher is checked
- **WHEN** npm workspace metadata is inspected
- **THEN** it references `distributions/npm`
- **AND** it does not reference `packages/ethos-node`
- **AND** the launcher forwards to the Python ETHOS command plane
