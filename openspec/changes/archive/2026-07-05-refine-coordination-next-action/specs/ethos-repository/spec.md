## ADDED Requirements

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance.

#### Scenario: Advisory unbound refs do not imply overlap remediation

- **GIVEN** a repository has an unbound `work/*` branch ref and no active
  overlapping or unknown Work Lane scope
- **WHEN** `ethos status --json` reports `data.coordination`
- **THEN** `blocking` is false
- **AND** `advisory_gaps` includes `unbound_work_lane_ref_present`
- **AND** `next_action` names unbound Work Lane ref cleanup rather than overlap
  or unknown-scope resolution
