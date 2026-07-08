# repository-governance Delta

## MODIFIED Requirements

### Requirement: Completed planning records do not remain active work

ETHOS SHALL archive completed planning records once their implementation has
been locally closed out, while preserving local-vs-remote publication boundaries.

#### Scenario: Completed plan residue is archived

- **WHEN** an ETHOS Work Lane discovers a completed plan whose implementation is
  already absorbed into local product truth
- **THEN** the plan, progress, and findings records are marked `state: archived`
- **AND** any stale unchecked closeout checklist item is closed with an explicit
  evidence boundary
- **AND** current plan navigation separates active or planned work from archived
  planning records
- **AND** remote publication is not claimed unless a separate hosted publication
  proof exists
