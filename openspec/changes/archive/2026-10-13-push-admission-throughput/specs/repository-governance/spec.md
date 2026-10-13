## ADDED Requirements

### Requirement: Publication push budget covers native pre-push admission

When `ethos publish` applies an exact peer transaction, the push deadline SHALL
be a fixed transfer allowance plus twice the admission measured for that peer
immediately before the push. The repository's native pre-push hook re-derives
that admission, so a fixed constant alone SHALL NOT bound it.

#### Scenario: Range-dependent hook admission

- **WHEN** the admission of a peer transaction takes longer than the transfer
  allowance
- **THEN** the push deadline still covers the transfer allowance plus twice
  that measured admission
- **AND** a push that exceeds the derived deadline is reported as an unknown
  outcome and reobserved, exactly as before.
