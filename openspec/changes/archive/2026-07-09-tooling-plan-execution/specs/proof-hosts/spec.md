## ADDED Requirements

### Requirement: Hosted provider observations remain evidence-class scoped

ETHOS SHALL capture hosted provider observation envelopes without treating local
tool discovery or provider CLI output as repository proof.

#### Scenario: Provider observation envelope is captured

- **WHEN** hosted provider observation runs in dry-run or execute mode
- **THEN** the evidence SHALL name GitHub and GitLab provider observation state
- **AND** it SHALL include the Git head, remote URL, command, tool availability,
  and execution state
- **AND** it SHALL explicitly set hosted GitHub status claimed, hosted GitLab
  status claimed, and remote publication claimed to false unless separate hosted
  facts are promoted through the publication evidence class.
