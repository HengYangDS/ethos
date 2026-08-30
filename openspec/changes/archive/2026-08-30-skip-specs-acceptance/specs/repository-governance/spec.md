## ADDED Requirements

### Requirement: Official spec-free Changes compile acceptance

ETHOS SHALL compile deterministic non-empty acceptance for a completed official
OpenSpec Change that explicitly declares `skip_specs: true` and contains no
requirement deltas. The acceptance SHALL use only official OpenSpec projection
facts and SHALL NOT require fake requirements, `commitment.toml`, or another
tracked intent carrier.

#### Scenario: Completed spec-free Change is selected

- **GIVEN** the official OpenSpec projection declares `skip_specs: true`
- **AND** its required proposal, design, and tasks artifacts are complete
- **AND** it contains no requirement deltas
- **WHEN** ETHOS compiles the selected Change
- **THEN** it produces one deterministic non-empty transient Commitment
- **AND** the Commitment remains applicable through the attested official archive transition

#### Scenario: Empty deltas are not implicitly accepted

- **WHEN** a Change has no requirement deltas but lacks the official spec-free declaration or completed artifacts
- **THEN** ETHOS fails closed with the exact OpenSpec acceptance gap
- **AND** no filename pattern, product category, compatibility carrier, or archived directory grants authority
