# repository-governance Delta

## MODIFIED Requirements

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance, and SHALL expose Work Lane
coordination small signals in focused reader summaries without granting foreign
lane authority.

#### Scenario: Lane status summary exposes coordination small signals

- **WHEN** `ethos lane status --json` reports `data.coordination`
- **THEN** `summary.foreign_work_lane_count` equals
  `data.coordination.foreign_work_lane_count`
- **AND** `summary.unbound_work_lane_count` equals
  `data.coordination.unbound_work_lane_count`
- **AND** `summary.missing_lease_count` equals
  `data.coordination.missing_lease_count`
- **AND** `summary.coordination_advisory_count` equals the number of
  `data.coordination.advisory_gaps`
- **AND** `summary.coordination_blocking` equals `data.coordination.blocking`
- **AND** `summary.coordination_next_action` equals
  `data.coordination.next_action`
- **AND** those summary fields remain derived visibility signals and do not grant
  write, land, retire, or cleanup authority over another Work Lane or ref
