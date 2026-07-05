## MODIFIED Requirements

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance, and SHALL expose unbound Work
Lane refs as inspectable residue objects rather than count-only signals.

#### Scenario: Advisory unbound refs expose subjects and relation

- **GIVEN** a repository has an unbound `work/*` branch ref
- **WHEN** `ethos status --json` reports `data.coordination`
- **THEN** `unbound_work_lane_refs` includes the branch, head, claim binding,
  relation to accepted truth, and next action
- **AND** `unbound_work_lane_count` equals the number of emitted residue objects
- **AND** the signal remains advisory unless another gate reports a required gap
