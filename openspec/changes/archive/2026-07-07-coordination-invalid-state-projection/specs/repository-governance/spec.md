## MODIFIED Requirements

### Requirement: Work Lane coordination signals are visible and measurable

ETHOS SHALL expose Work Lane coordination facts without granting write, land, or
retire authority over foreign lanes. Coordination required and advisory gaps
SHALL be projected into the shared invalid-state taxonomy so small coordination
signals are visible, classifiable, and auditable.

#### Scenario: Coordination advisories classify without blocking

- **GIVEN** a repository has a foreign Work Lane with no lease
- **WHEN** `ethos status --json` builds `data.coordination`
- **THEN** `advisory_gaps` includes `foreign_work_lane_present` and `work_lane_missing_lease:<branch>`
- **AND** `invalid_states.categories.change_unbounded` contains both advisory gaps
- **AND** `blocking` remains false unless required coordination gaps are present
