## MODIFIED Requirements

### Requirement: Governed Repository Governance
ETHOS SHALL govern repositories through one governed repository semantic model.

#### Scenario: Governance context is shared

- **WHEN** ETHOS emits audit, proof, or report payloads for any governed repository
- **THEN** the payload includes `governance_context`
- **AND** the context identifies the subject as a repository
- **AND** every profile uses the same transition command semantics for status,
  plan, prove, land, and publish
- **AND** every profile classifies orient as a separate read-only reader-view
  command
- **AND** every profile classifies report as a separate read-only scorecard command
- **AND** profile or adapter differences do not create a second product command
  plane
- **AND** first-glance product docs name this as Isomorphic Governance without
  turning governed repositories into product clones.
