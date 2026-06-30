## ADDED Requirements

### Requirement: Complete Adoption Skeleton
ETHOS SHALL scaffold repository governance surfaces for `.ethos`, official
OpenSpec records, repo-local skills, docs, claims, evidence, and hosted CI
projections.

#### Scenario: A repository is adopted
- **WHEN** `ethos adopt --profile gitlab --apply` runs on an empty repository
- **THEN** the planned and written files include ETHOS config, official
  OpenSpec specs, `.agents/skills`, docs, claims, evidence, and GitLab CI

### Requirement: Fleet Inspection
ETHOS SHALL inspect an external repository as an adopter through repository
surfaces rather than product-core hardcoded names.

#### Scenario: An adopter is inspected
- **WHEN** `ethos fleet inspect --target <repo> --json` runs
- **THEN** ETHOS reports adopter governance surfaces and required gaps without
  embedding adopter-specific package names into the kernel
