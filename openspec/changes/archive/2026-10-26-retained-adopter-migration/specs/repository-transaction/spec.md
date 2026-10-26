## ADDED Requirements

### Requirement: Retained runtime selection is independent of activation coordination

ETHOS SHALL let its qualified coordinator select an explicit manifest-bound adopter runtime
without requiring that runtime to share the coordinator's dependency lock or launcher spelling.
Self-hosted ETHOS SHALL retain accepted-source authority. Complete runtime identity, exact wheel,
physical repository scope and fresh effect-time admission SHALL remain required.

#### Scenario: A qualified successor restores retained predecessor supply

- **WHEN** an adopter selects an exact validated predecessor through its qualified successor
- **THEN** the existing activation owner preserves retained state and selects that predecessor
- **AND** the supplied predecessor does not have to coordinate rollback of newer supply.

#### Scenario: A supplied runtime conflicts with self-hosted accepted authority

- **WHEN** explicit supply does not match the current self-hosted accepted build
- **THEN** activation refuses without changing selected runtime or retained repository state.

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
