## ADDED Requirements

### Requirement: Archive authority survives an authorized base refresh

ETHOS SHALL preserve the exact archived Change authority when an authorized
Work Lane base refresh rewrites the archive commit. The recovered authority
MUST be derived from the existing archive effect and exact refresh evidence,
and MUST remain bound to the same Change identity and archive post-image.

#### Scenario: Archived lane is refreshed onto a newer candidate

- **GIVEN** a Work Lane archived one official OpenSpec Change through an
  attested archive effect
- **AND** an authorized base refresh rewrote that archive commit onto a newer
  candidate
- **WHEN** ETHOS resolves archive authority for the refreshed Work Lane
- **THEN** it derives the rewritten archive tip from the archive and refresh
  Attestations
- **AND** it recognizes the same archived Change and post-image as authority

#### Scenario: A nearer unrelated archive exists after refresh

- **GIVEN** the refreshed Work Lane history contains an archive for another
  Change nearer to `HEAD`
- **WHEN** ETHOS resolves archive authority for the Work Lane's archived Change
- **THEN** it MUST NOT substitute the unrelated archive
- **AND** proof planning remains bound to the Work Lane's exact archived Change

#### Scenario: Refresh evidence is missing or ambiguous

- **WHEN** ETHOS cannot derive one exact rewritten archive tip from valid
  archive and refresh Attestations
- **THEN** archive authority resolution fails closed
- **AND** ETHOS does not infer continuity from content similarity, patch
  identity, path proximity, or another archived Change
