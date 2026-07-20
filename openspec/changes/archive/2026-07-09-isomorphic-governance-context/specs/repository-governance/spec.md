# repository-governance Delta

## MODIFIED Requirements

### Requirement: Governed Repository Governance

ETHOS SHALL govern repositories through one governed repository semantic model.

#### Scenario: Primary command results expose the shared governance context

- **WHEN** ETHOS emits `status`, `plan`, `prove`, `land`, `publish`, `orient`, or
  `report` JSON for any governed repository
- **THEN** the top-level result includes `governance_context`
- **AND** the context identifies the subject as a repository
- **AND** every profile uses the same transition command semantics for status,
  plan, prove, land, and publish
- **AND** every profile classifies orient as a separate read-only reader-view
  command
- **AND** every profile classifies report as a separate read-only scorecard
  command
- **AND** profile or adapter differences do not create a second product command
  plane
- **AND** command-specific `data` payloads remain governed by their own native
  schema or domain contract rather than becoming a second truth store.
