## ADDED Requirements

### Requirement: Remote reconciliation continuation preserves historical carrier boundaries

When a historical remote-reconciliation carrier promoted its delta but lifecycle work remains unfinished, ETHOS SHALL preserve the historical archive without false completion and bind an active continuation to the same episode claim before remaining closeout work proceeds.

#### Scenario: remaining lifecycle work continues after historical archival

- **WHEN** a historical reconciliation archive records unfinished local closeout, remote observation, or retirement work
- **THEN** an active continuation records the transfer and binds the episode claim
- **AND** it preserves normal merge and no-force constraints
- **AND** it distinguishes local proof, remote mutation, remote observation, and hosted-provider observation
