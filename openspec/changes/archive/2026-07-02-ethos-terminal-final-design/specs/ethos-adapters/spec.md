## ADDED Requirements

### Requirement: Lifecycle Review Covers Active Changes

ETHOS SHALL review all active OpenSpec changes in lifecycle mode when no single
change is explicitly selected.

#### Scenario: Multiple active changes are reviewed

- **WHEN** `ethos openspec --lifecycle --json` runs without `--change`
- **THEN** lifecycle output includes every active change reported by official
  OpenSpec list output
- **AND** each change is checked for carriers, claim binding, proposal metadata,
  capability profile health, and out-of-scope boundaries.
