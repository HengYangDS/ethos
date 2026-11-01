## ADDED Requirements

### Requirement: A focused proof names the proof that meets the quality floor

A focused proof that selects a code-correctness gate SHALL keep every axis of the repository's code
correctness map. When its only refusals are unproven axes that it did not select, its next action
SHALL be `ethos prove --execute --json`.

#### Scenario: One axis of a multi-axis map is selected

- **WHEN** `ethos prove --execute --gate <gate-id> --json` selects the gate of one axis of a code
  correctness map that maps several
- **THEN** the proof refuses with `quality_obligation_unproven:<axis>` for each unselected axis
- **AND** its next action is `ethos prove --execute --json`
