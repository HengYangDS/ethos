# command-plane Delta

## MODIFIED Requirements

### Requirement: Explain Command Projects Invalid-State Signals

ETHOS SHALL expose `ethos explain` as a read-only invalid-state taxonomy
projection for governance gaps and advisory signals.

#### Scenario: Explain generated usage names gaps or signals

- **WHEN** a human or agent reads generated `ethos explain --help` output
- **THEN** the usage line presents the positional input as `GAP-OR-SIGNAL`
- **AND** the parameter table presents the positional input as `GAP-OR-SIGNAL`
- **AND** JSON result compatibility still exposes the original string as `gap`
- **AND** the command remains a read-only invalid-state projection
