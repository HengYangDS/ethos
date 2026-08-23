## ADDED Requirements

### Requirement: Repository Commitment admission is precise and pre-effect
ETHOS SHALL observe the repository Commitment through one strict current-schema
owner before any fresh Work Lane effect. The observation SHALL distinguish an
absent carrier, unreadable or syntactically invalid bytes, an unsupported schema,
semantic validation failure, and repository identity mismatch. Every consumer
SHALL preserve that classification instead of translating it to absence.

#### Scenario: Present obsolete carrier is not reported missing
- **WHEN** the exact repository tree contains `.ethos/commitment.toml` but the carrier does not satisfy the current Commitment schema
- **THEN** ETHOS reports the precise unsupported or invalid carrier state
- **AND** it does not report `repository_commitment_missing`

#### Scenario: Fresh lane dry-run and apply share preflight
- **WHEN** fresh Work Lane creation targets a repository whose Commitment cannot be admitted
- **THEN** dry-run and apply return the same primary blocker from the same repository identity and tree
- **AND** apply creates no ref, worktree, Lease, or Change carrier

#### Scenario: Zero-effect failure has a truthful receipt
- **WHEN** fresh Work Lane creation fails before its first effect
- **THEN** the result preserves the original admission failure
- **AND** it reports the observed absence of transaction residue
- **AND** it does not report cleanup or compensation failure

#### Scenario: Downstream consumers preserve producer classification
- **WHEN** plan, proof, publication, or lane admission consumes a failed repository Commitment observation
- **THEN** each projection retains the same precise primary blocker
- **AND** no consumer reclassifies invalid presence as missing absence
