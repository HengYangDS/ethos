## MODIFIED Requirements

### Requirement: Pure Kernel Package

ETHOS core SHALL contain the IO-free kernel, contracts, and quality primitives needed by the product runtime.

#### Scenario: Pure leaves collapse into ethos-core

- **WHEN** package topology is evaluated after the structural migration
- **THEN** contracts and quality modules resolve under `ethos_core`
- **AND** no retired `ethos-contracts` or `ethos-quality` package remains as a compatibility shell.
