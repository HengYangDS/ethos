## ADDED Requirements

### Requirement: Stage-0 parity projection recovery is exact

During a sanctioned Work Lane refresh, a generated parity projection conflict
SHALL be recoverable only when its exact stage-0 index payload is structurally
valid and belongs to the same adopter encoded by the conflicted path; source
conflicts SHALL remain blocked.

#### Scenario: rerere stages a valid parity projection

- **WHEN** a sanctioned refresh reports an unmerged
  `evidence/parity/<adopter>-shadow.json` path
- **AND** index stage 0 parses as schema version `1` JSON with that exact
  `<adopter>` identity
- **THEN** ETHOS SHALL preserve that staged projection and continue the replay
- **AND** it SHALL require fresh parity regeneration before proof.

#### Scenario: staged projection does not prove exact identity

- **WHEN** a conflicted parity path has no stage-0 JSON blob, malformed JSON,
  unsupported schema version, or a different adopter identity
- **THEN** ETHOS SHALL NOT trust the staged content as a resolved projection
- **AND** it SHALL use the existing bounded projection fallback or block as a
  real conflict.
