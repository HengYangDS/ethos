## ADDED Requirements

### Requirement: Authority Graph Read Model
ETHOS SHALL expose a DocOS authority graph read model for current product
truth relations.

#### Scenario: Authority graph is audited
- **WHEN** `ethos audit --mode shape --json` runs
- **THEN** the result includes an authority graph report
- **AND** every graph entry has an owner, relation type, stable path, and
  typed derivation or supersession relations
- **AND** the graph reports drift gaps without becoming a lifecycle owner

### Requirement: Adopter First-Hour Contract
ETHOS SHALL provide a first-hour adopter path that starts read-only and
explains profile choice before mutation.

#### Scenario: Adoption dry-run is inspected
- **WHEN** `ethos adopt --profile python --dry-run --json` runs
- **THEN** the result reports read files, planned files, apply criteria, and
  rollback instructions
- **AND** `python-package` remains a compatibility alias for `python`
