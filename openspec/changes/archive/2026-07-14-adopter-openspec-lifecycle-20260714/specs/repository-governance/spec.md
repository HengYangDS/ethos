## ADDED Requirements

### Requirement: Universal adopter OpenSpec lifecycle

ETHOS SHALL evaluate official OpenSpec lifecycle during plan and proof for every
governed root, including a valid adopter profile. Lifecycle gaps SHALL remain
OpenSpec/repository-governance gaps and SHALL NOT be represented as
`code_correctness_gates` or method-package authority.

#### Scenario: Valid adopter has an invalid Change lifecycle
- **WHEN** the adopter runs plan or prove
- **THEN** the lifecycle payload and its required gap are returned
- **AND** the command is not clean merely because the root is not the product.
