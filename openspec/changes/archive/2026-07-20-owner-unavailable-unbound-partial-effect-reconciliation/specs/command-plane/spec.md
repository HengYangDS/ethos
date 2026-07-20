## MODIFIED Requirements

### Requirement: Semantic Lane Lifecycle Groups

ETHOS SHALL group lease, handoff, exceptional resolution, and retirement under
semantic nested command families.

#### Scenario: retirement commands are grouped

- **WHEN** maintainers inspect the Lane command plane
- **THEN** bounded retirement commands are `ethos lane retire landed`,
  `ethos lane retire superseded`, `ethos lane retire unbound`, and
  `ethos lane retire reconcile-ref-absent`
- **AND** lease lifecycle is under `ethos lane lease`, handoff under
  `ethos lane handoff`, and exceptional judgment under `ethos lane resolution`.
