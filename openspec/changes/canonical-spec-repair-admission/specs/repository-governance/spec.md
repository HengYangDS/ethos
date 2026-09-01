## MODIFIED Requirements

### Requirement: OpenSpec Lifecycle Contract Review

ETHOS SHALL compose official OpenSpec validation with one transient Commitment
compiled from each selected active Change. Official proposal, specs, design,
tasks, metadata, configuration, and exact repairs named by current official
canonical-spec validation failures are the sole tracked intent and lifecycle
carriers; no `commitment.toml`, `scope.toml`, local template, or Change README is
required.

#### Scenario: Active OpenSpec Change is lifecycle complete

- **GIVEN** an active OpenSpec Change has every artifact required by its official schema
- **WHEN** ETHOS audits lifecycle or compiles a plan
- **THEN** it validates the official Change and deterministically compiles acceptance intent
- **AND** no parallel tracked carrier participates

#### Scenario: Active OpenSpec Change lacks its contract

- **WHEN** an official required artifact is missing, invalid, or incomplete
- **THEN** ETHOS reports the exact official artifact or task gap
- **AND** no bootstrap, claim, archive scan, or parallel metadata grants authority

#### Scenario: Official validation requires a canonical spec repair

- **GIVEN** official strict validation reports
  `openspec_validation_failed:spec:<capability>`
- **AND** that failure blocks ordinary material-scope resolution
- **WHEN** the current Work Lane requests prewrite for exactly
  `openspec/specs/<capability>/spec.md`
- **THEN** ETHOS admits that exact repair path under the selected active Change
- **AND** unrelated canonical specifications and all non-specification paths
  remain blocked
- **AND** malformed or ambiguous capability identifiers grant no authority
