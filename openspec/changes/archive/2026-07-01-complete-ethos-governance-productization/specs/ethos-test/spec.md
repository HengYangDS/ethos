## ADDED Requirements

### Requirement: Governance Lifecycle Fixtures
ETHOS SHALL provide reusable tests and fixtures for complete and malformed
governance lifecycles.

#### Scenario: Complete lifecycle fixture passes
- **WHEN** tests load a complete governance lifecycle fixture
- **THEN** claim admission, OpenSpec lifecycle review, proof evidence, and
  promotion target validation all report no required gaps

#### Scenario: Malformed lifecycle fixture fails
- **WHEN** tests load a malformed governance lifecycle fixture
- **THEN** ETHOS reports specific required gaps for missing claim binding,
  missing promotion target, missing executed proof, or malformed OpenSpec
  carrier state

### Requirement: Reference Adopter Boundary Fixtures
ETHOS SHALL test adopter parity through generic profiles instead of core
package adopter terminology.

#### Scenario: Reference adopter fixture is validated
- **WHEN** tests validate a reference adopter profile fixture
- **THEN** adopter-specific terms remain in the fixture or evidence
- **AND** core product packages remain provider-neutral
