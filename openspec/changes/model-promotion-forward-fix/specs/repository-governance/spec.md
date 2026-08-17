## ADDED Requirements
### Requirement: Publication selects repository authority
ETHOS SHALL select the exact accepted-HEAD repository Commitment proof.
#### Scenario: Historical or conflicting proof shares the HEAD
- **WHEN** repository and retired Work Lane proofs share the accepted HEAD
- **THEN** only exact repository authority SHALL apply, or fail closed on conflict.
