## MODIFIED Requirements

### Requirement: Invalid repository profile commands return structured blocks

Every public ETHOS reader, planning, proof, landing, publication, and OpenSpec lifecycle command
SHALL return a structured `EthosResult` when the target repository profile is invalid. The result
SHALL contain the stable invalid-profile gap and SHALL not emit an uncaught traceback as its command
result. It SHALL name each validation problem in `data.profile_problems` by its kind and key path,
never by its value.

#### Scenario: JSON reader observes an invalid profile

- **WHEN** `ethos status --json` targets an invalid repository profile
- **THEN** it SHALL emit parseable JSON with `verdict = block`
- **AND** `required_gaps` SHALL contain `repository_profile_invalid:.ethos/profile.toml`.

#### Scenario: Enforcing proof command observes an invalid profile

- **WHEN** `ethos prove --json` targets an invalid repository profile
- **THEN** it SHALL emit parseable blocked JSON and exit non-zero
- **AND** it SHALL not start a mutation or create proof evidence.

#### Scenario: Landing does not mask an invalid adopter profile

- **WHEN** `ethos land --json` targets an invalid repository profile
- **THEN** it SHALL emit parseable JSON with the invalid-profile gap before reporting another
  mutation-admission gap
- **AND** `ethos land --apply --json` SHALL exit non-zero after emitting that same structured
  result.

#### Scenario: An old profile names the keys to migrate

- **WHEN** a profile carries a key the profile model rejects, such as `schema_version`
- **THEN** `data.profile_problems` names it as `extra_forbidden:schema_version`
- **AND** no profile value appears in the result.
