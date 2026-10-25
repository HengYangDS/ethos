## ADDED Requirements

### Requirement: Retained authoring identities have a native migration

ETHOS SHALL provide an exactly admitted migration from retained authoring
identities to current identities, preserving authored content, index intent,
task acceptance and lane-holder coordination. Migration SHALL use existing
native effect and recovery owners without retaining a parallel authority.

#### Scenario: An owned retained topic needs current authoring

- **WHEN** the current holder requests migration of an exact retained topic
- **THEN** preview identifies its source, destination and current authority
- **AND** apply preserves its content and index intent while migrating identity
- **AND** current admission recognizes the same holder and retained acceptance.

#### Scenario: A retained active Change needs current identity

- **WHEN** the owner requests migration of an exact retained active Change
- **THEN** the native carrier operation preserves task identities and acceptance
- **AND** normal authoring resumes without a permanent legacy-name alias.

#### Scenario: Required coordinates drift or the destination exists

- **WHEN** source content, refs, holder generation or destination no longer matches preview
- **THEN** migration refuses before effect and preserves the observed resources.

#### Scenario: Projection fails after the attested ref effect

- **WHEN** the exact ref effect succeeds but a retained-resource projection fails
- **THEN** recovery identifies and completes that projection forward
- **AND** it does not reverse the attested ref or discard retained content.
