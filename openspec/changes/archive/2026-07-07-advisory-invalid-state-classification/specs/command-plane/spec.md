# command-plane Delta

## MODIFIED Requirements

### Requirement: Explain Command Projects Invalid-State Signals

ETHOS SHALL expose invalid-state taxonomy projection for governance gaps and
advisory signals without making advisory signals lifecycle blockers.

#### Scenario: Report advisory signals classify without blocking

- **WHEN** `ethos report --json` includes non-blocking advisory signals
- **THEN** the advisory signal layer includes an `invalid_states` projection over those signals
- **AND** advisory signals may classify into carrier, claim, evidence, authority, subject, commitment, chronicle, or substrate failure categories
- **AND** the advisory layer keeps `blocking=false` and `required_gaps=[]`
- **AND** advisory next actions remain bounded inspection or explanation hints
