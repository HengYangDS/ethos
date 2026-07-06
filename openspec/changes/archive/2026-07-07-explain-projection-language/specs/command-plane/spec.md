# command-plane Delta

## MODIFIED Requirements

### Requirement: Explain Command Projects Invalid-State Signals

ETHOS SHALL expose `ethos explain` as a read-only invalid-state taxonomy
projection for governance gaps and advisory signals.

#### Scenario: Explain help and docs use gap-or-signal language

- **WHEN** a human or agent reads `ethos explain --help` or the command-plane reference
- **THEN** the command is described as explaining a governance gap or advisory signal
- **AND** docs show `ethos explain <gap-or-signal>` rather than a required-gap-only surface
- **AND** the command remains a read-only projection, not a lifecycle command
