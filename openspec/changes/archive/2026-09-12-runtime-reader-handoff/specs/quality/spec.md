## ADDED Requirements

### Requirement: Proof validation is independent of optional intent

Every proof-execution TransitionPlan SHALL validate the same supported semantic
fields whether its transient Commitment is present or absent. Immutable Mapping
containers SHALL NOT bypass validation.

#### Scenario: Unsupported Facts are rejected in both proof modes

- **WHEN** a proof plan carries an unsupported Facts field with or without Commitment
- **THEN** compilation rejects the model gap before any proof or Git effect

### Requirement: Secret admission requires credential evidence

Secret scanning SHALL recognize supported credential forms and credential-bearing
assignments without treating unrelated content-addressed Git identities as
credentials solely because a provider name appears elsewhere in the source.

#### Scenario: Referenced source identity is not a provider credential

- **WHEN** research names a provider and contains valid Git commit and tree IDs
- **THEN** the native scanner accepts that non-credential source

#### Scenario: Credential forms remain rejected

- **WHEN** source contains a provider-prefixed token or an unprefixed token assignment
- **THEN** the same native scanner rejects it without a file-specific exception
