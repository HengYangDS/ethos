## ADDED Requirements

### Requirement: Curated JSON Evidence Carrier Admission

ETHOS SHALL keep tracked JSON placement fail-closed and SHALL admit a curated
Chronicle JSON evidence carrier only when the format-selection policy names its
exact repository-relative file path.

#### Scenario: Exact convergence inventory is admitted

- **WHEN** the tracked Work Lane convergence inventory is present at
  `evidence/chronicle/all-work-lanes-convergence-20260716/lane-inventory.json`
- **THEN** the format-selection owner script accepts that exact file as a
  declared JSON carrier
- **AND** the audit remains clean when every other JSON path satisfies its
  declared carrier boundary.

#### Scenario: Unlisted Chronicle JSON remains blocked

- **WHEN** a tracked JSON file appears under `evidence/chronicle/` without an
  exact file declaration
- **THEN** the format-selection owner script reports that JSON as outside its
  declared carrier home
- **AND** no broad Chronicle-root allowance is inferred.
