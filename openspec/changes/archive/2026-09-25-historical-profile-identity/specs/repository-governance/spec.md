## ADDED Requirements

### Requirement: Historical effect identity survives profile schema evolution

ETHOS SHALL validate repair and Git-ref-effect Attestations against each exact
former commit's stable repository identity declaration, not today's full
profile schema. Missing, malformed or mismatched historical identity SHALL
block without current-profile or caller fallback. Current effects SHALL still
require the strict current profile, repair coordinates, policy and payload
digests, replacement history, effect Attestations, source proof, ref role and
exact remote CAS.

#### Scenario: Retired profile field does not erase a valid repair

- **GIVEN** a completed exact repair of a former accepted commit whose profile
  declares the same repository ID and a field removed from the current schema
- **WHEN** publication checks a declared peer still holding an original commit
  covered by that repair
- **THEN** provenance validation uses the former commit's stable identity
- **AND THEN** the old field alone does not block the repaired-history relation
- **AND THEN** current proof, target policy and remote CAS remain independent
  conditions before any effect.

#### Scenario: Accepted closeout remains verifiable after profile cleanup

- **GIVEN** a completed candidate-to-accepted effect whose former commit has
  the same repository ID but a field later removed from the profile schema
- **WHEN** publication revalidates the accepted effect at the new source HEAD
- **THEN** its recorded Git effect remains verifiable against the former
  commit's stable repository identity
- **AND THEN** it does not report the accepted closeout as unattested solely
  because the former profile has an obsolete field.

#### Scenario: Historical identity cannot be guessed

- **WHEN** the former profile is absent, unreadable, syntactically malformed,
  declares no nonempty repository ID, or declares a different repository ID
- **THEN** historical repair or effect provenance is rejected before publication
- **AND THEN** the current profile, receipt text or peer name does not replace
  the former commit's identity.

#### Scenario: Other repair bindings remain mandatory

- **WHEN** the historical identity matches but the recorded policy or commit
  payload digest, signed replacement relation, effect Attestation or current
  source proof is invalid
- **THEN** the corresponding existing admission blocks publication
- **AND THEN** no peer ref changes.

#### Scenario: Current profile remains strict

- **WHEN** the current checkout's profile violates the current typed schema
- **THEN** status, planning, proof and publication remain blocked
- **AND THEN** historical identity tolerance cannot validate the current
  operational profile.
