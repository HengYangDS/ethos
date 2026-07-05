## MODIFIED Requirements

### Requirement: Terminal Package Ontology

ETHOS SHALL report the terminal package ontology as exactly `ethos-core` plus `ethos`.

#### Scenario: Package ontology validates two-package target

- **WHEN** package ontology, workspace members, import-linter contracts, and type policy are checked
- **THEN** all product package targets reduce to `ethos-core` and `ethos`
- **AND** package-bound gates fail if retired package directories or sources reappear.
