## MODIFIED Requirements

### Requirement: Kernel Chain
ETHOS SHALL model repository operation through the kernel chain
Authority, Subject, Commitment, Change, Evidence, Claim, and Chronicle.
The chain SHALL preserve the root text as a judgment constraint without turning
that text into a subsystem, feature map, or low-level implementation label.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through kernel objects without depending
  on repository, assistant, adapter, adopter, or hosted-runner packages
- **AND** Claim binds evidence rather than owning lifecycle state
- **AND** semantic claims require a semantic verifier

#### Scenario: Root text remains canonical and restrained
- **WHEN** ETHOS adds or changes an active code, config, hook, system contract, or
  provider projection surface
- **THEN** that surface cites concrete engineering invariants rather than philosophical labels
  or numbered philosophy references
- **AND** the canonical root text remains in the Product Design Contract rather
  than being duplicated into machine-adjacent derived files
- **AND** derived axiom files remain subordinate to product docs and do not create
  a new truth center
