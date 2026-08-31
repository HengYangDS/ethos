## ADDED Requirements

### Requirement: Hosted repository proof preserves source authority

Hosted repository proof SHALL execute the proposal checkout's locked source
environment without first installing or selecting repository-local mutation
hooks or an accepted package runtime. Repository source audit SHALL not treat
the host's hook/runtime projection as proof of source correctness.

#### Scenario: Proposal commit differs from accepted runtime source

- **GIVEN** a hosted checkout contains a proved proposal commit whose source
  identity differs from the repository's accepted package runtime
- **WHEN** the repository proof job executes
- **THEN** proof runs directly from the checkout's locked source environment
- **AND** no hook/runtime activation is attempted before proof
- **AND** the source proof is not rejected solely because a local mutation
  runtime is absent or bound to the accepted commit.

#### Scenario: Local mutation readiness remains independently observable

- **WHEN** a user inspects a mutable local checkout
- **THEN** status reports its selected hook/runtime currentness
- **AND** repository source audit neither hides nor assumes that separate local
  mutation-readiness fact.
