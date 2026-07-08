## MODIFIED Requirements

### Requirement: Kernel Chain
ETHOS SHALL model repository operation through the kernel chain
JudgmentSource, Subject, Commitment, Change, Evidence, Claim, and Chronicle.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through kernel objects without
  depending on repository, assistant, adapter, adopter, or hosted-runner
  packages
- **AND** Claim binds evidence rather than owning lifecycle state
- **AND** semantic claims require a semantic verifier
