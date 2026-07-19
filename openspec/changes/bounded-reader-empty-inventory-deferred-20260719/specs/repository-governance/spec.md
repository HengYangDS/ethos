## ADDED Requirements

### Requirement: Bounded Coordination Aggregate Detail State

ETHOS SHALL derive coordination aggregate detail state from the reader mode
selected by the caller, not from the number or contents of visible foreign Work
Lane rows.

#### Scenario: Empty bounded inventory remains deferred

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `workspace_status` runs with foreign path-scope expansion disabled
- **THEN** coordination `detail_state` SHALL be `deferred`
- **AND** `dirty_foreign_work_lane_count`, `overlap_count`,
  `unknown_scope_count`, `closeout_residue_count`, and
  `dirty_closeout_residue_count` SHALL be `null`
- **AND** observable foreign-lane and lease counts SHALL remain available.

#### Scenario: Empty full inventory remains exact

- **GIVEN** no foreign Work Lane is visible
- **WHEN** `workspace_status` runs in its full default mode
- **THEN** coordination `detail_state` SHALL be `exact`
- **AND** `dirty_foreign_work_lane_count`, `overlap_count`,
  `unknown_scope_count`, `closeout_residue_count`, and
  `dirty_closeout_residue_count` SHALL all be zero.
