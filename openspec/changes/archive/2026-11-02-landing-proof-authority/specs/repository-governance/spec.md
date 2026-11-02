## ADDED Requirements

### Requirement: Landing binds the intent its admitted proof carries

`ethos land` SHALL take its candidate authority from the Change that its admitted proof carries,
compiled at the landed head, so readiness, proof admission and the candidate effect select one
intent. A carried encoding that is not admissible at the head SHALL still refuse landing.

#### Scenario: A proof of an earlier archived Change lands

- **GIVEN** a Work Lane that archived two Changes and holds an admitted proof of the first at its
  head
- **WHEN** land applies without a Change selection
- **THEN** the candidate effect binds the first Change's Commitment
- **AND** the candidate branch moves to the head

#### Scenario: An encoding that is not admissible at the head is refused

- **WHEN** no admissible encoding of the carried Change at the head matches the admitted proof
- **THEN** land refuses with `proof_attestation_authority_binding_mismatch`
- **AND** the candidate branch does not move
