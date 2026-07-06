# command-plane Delta

## MODIFIED Requirements

### Requirement: Explain Command Projects Invalid-State Signals

ETHOS SHALL expose `ethos explain` as a read-only invalid-state taxonomy
projection for governance gaps and advisory signals.

#### Scenario: Explain accepts advisory signals without required-gap overclaim

- **WHEN** `ethos explain <signal> --json` runs for a non-blocking advisory signal
- **THEN** the payload keeps the original string as `gap` for compatibility
- **AND** the payload also exposes the original string as `signal`
- **AND** the payload classifies the signal into an invalid-state category
- **AND** the payload wording does not claim every explained signal is a required gap
- **AND** the taxonomy projection does not become a lifecycle command
