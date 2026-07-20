## ADDED Requirements

### Requirement: Candidate-current external-adopter observations remain bounded and durable

ETHOS SHALL preserve a dated, local provider-neutral observation at a named
candidate product revision against an isolated clone of an existing adopter.
The record SHALL bind product and adopter revisions, raw-bundle digest,
overlay outcome, command-parity result, and explicit non-authority boundaries.

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** generic overlay adoption encounters pre-existing adopter-owned ETHOS
  profile, skills, or control surfaces
- **THEN** the observation SHALL record the fail-closed conflict outcome
- **AND** it SHALL NOT state that the generic overlay replaced those surfaces
- **AND** the source adopter checkout SHALL remain unchanged.

#### Scenario: Candidate runtime and native command surfaces are compared

- **WHEN** an isolated adopter clone exposes a repository-native ETHOS command
  surface and the candidate product runtime can address the clone
- **THEN** the record SHALL bind both revisions and the shared command count
- **AND** it SHALL record semantic-difference and false-negative outcomes
- **AND** it SHALL NOT claim semantic correctness, hosted-provider execution,
  remote publication, authority, or independent review from that comparison.

#### Scenario: Latest routing preserves dated history

- **WHEN** a newer candidate-current observation is promoted
- **THEN** documentation routes SHALL point to that dated canonical record
- **AND** earlier dated Chronicles SHALL remain historical records rather than
  being rewritten in place.
