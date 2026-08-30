## ADDED Requirements

### Requirement: Full proof covers hosted offline quality owners

ETHOS SHALL include every required offline repository-quality owner used by
hosted acceptance in its canonical full proof set.

#### Scenario: Repository hygiene fails before publication

- **WHEN** tracked source contains a forbidden quality suppression
- **THEN** the exact-HEAD full proof fails through the repository-hygiene gate
- **AND** hosted CI does not become the first observer of that defect.
