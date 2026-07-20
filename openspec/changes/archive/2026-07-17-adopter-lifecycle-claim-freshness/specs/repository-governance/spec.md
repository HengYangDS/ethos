## ADDED Requirements

### Requirement: Lifecycle claim semantic scope is behavior-exact

An active claim that attests universal adopter OpenSpec lifecycle SHALL declare `semantic_scope` promotion targets for the lifecycle command implementations and their behavioral regressions. It SHALL NOT use a broad CLI directory merely because the implementation resides there. The semantic-scope reader SHALL fail closed when any declared lifecycle implementation or regression target changes.

#### Scenario: Unrelated CLI reader change does not stale lifecycle evidence

- **WHEN** a change outside the declared lifecycle implementation and regression targets changes a CLI reader file
- **THEN** the lifecycle claim semantic digest remains current
- **AND** the claim reader does not emit `evidence.semantic_scope_stale`

#### Scenario: Lifecycle implementation change stales lifecycle evidence

- **WHEN** a declared lifecycle command implementation or behavioral regression target changes
- **THEN** the lifecycle claim reader emits `evidence.semantic_scope_stale`
- **AND** ETHOS requires a governed evidence refresh before the claim is clean
