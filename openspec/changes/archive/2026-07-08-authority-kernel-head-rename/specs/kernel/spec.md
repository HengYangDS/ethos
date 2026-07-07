## MODIFIED Requirements

### Requirement: Kernel Chain
ETHOS SHALL model repository operation through the kernel chain
Authority, Subject, Commitment, Change, Evidence, Claim, and Chronicle.

#### Scenario: Current kernel head is Authority
- **WHEN** ETHOS projects current governance context, schemas, docs, or kernel models
- **THEN** the head node is named `Authority`
- **AND** no tracked code, schema, docs, evidence, or OpenSpec surface exposes predecessor vocabulary
- **AND** archived evidence and archived OpenSpec records preserve history while using current vocabulary
