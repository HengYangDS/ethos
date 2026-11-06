## ADDED Requirements

### Requirement: An operator can run the readiness tier alone

`ethos prove --readiness --execute` SHALL run exactly the readiness gates of the repository's full
proof plan, without waiting for the proof slot or host load. It SHALL report every test and package
gate as not run, SHALL write no proof attestation, and SHALL pass only when every readiness gate
passes.

#### Scenario: Every readiness gate passes

- **WHEN** an operator runs `ethos prove --readiness --execute` and every readiness gate passes
- **THEN** the result passes and names each test and package gate as not run
- **AND** no proof attestation is written, so landing cannot admit it

#### Scenario: A readiness gate fails

- **WHEN** one readiness gate fails
- **THEN** the result does not pass and keeps that gate's evidence
