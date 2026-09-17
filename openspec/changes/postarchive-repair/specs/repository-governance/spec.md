## MODIFIED Requirements

### Requirement: OpenSpec Lifecycle Contract Review

ETHOS SHALL compose official OpenSpec validation with one transient Commitment
compiled from each selected official Change snapshot. Official proposal, specs, design,
tasks, metadata, configuration, and exact repairs named by current structured
official validation failures are the sole tracked intent and lifecycle
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
  or its verified archived source
- **AND** unrelated canonical specifications and all non-specification paths
  remain blocked
- **AND** malformed or ambiguous capability identifiers grant no authority

#### Scenario: Official validation requires an active Change artifact repair

- **GIVEN** one selected active Change has a complete official artifact graph
- **AND** current strict validation marks that exact Change invalid and reports
  a structured `ERROR` or `WARNING` issue path
- **AND** that issue path resolves uniquely against the Change root or its
  `specs/` root to one existing output in the official artifact graph
- **AND** the official output retains its lexical path beneath the repository
  root and that exact path is a non-symlink regular file
- **WHEN** the owning Work Lane requests prewrite for exactly that output
- **THEN** ETHOS admits only that exact repair path without first requiring a
  valid Commitment
- **AND** malformed, absolute, traversing, missing, ambiguous,
  unrelated-Change, symlinked, non-regular, directory-wide, and mixed paths
  remain blocked
- **AND** an `INFO` issue grants no repair authority
- **AND** the repair authority disappears when fresh strict validation no longer
  reports the matching issue.


#### Scenario: Official archive leaves a canonical validation failure

- **GIVEN** no active Change remains and exact completed archive evidence
  identifies the selected Change and its canonical specification output
- **AND** current official strict validation reports a blocking structured
  issue for that canonical specification
- **WHEN** the currently coordinated Work Lane requests that exact repair path
- **THEN** prewrite and host admission permit only the validator-named repair
- **AND** current runtime, actor, Lease and supplied postimage checks still apply
- **AND** missing or mismatched archive evidence, unrelated validation failures
  and additional requested paths do not acquire repair permission
- **AND** the repaired source requires fresh strict validation and proof without
  recreating the active Change or repeating its completed archive effect
