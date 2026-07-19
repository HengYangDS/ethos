## ADDED Requirements

### Requirement: Lifecycle mutation has one semantic owner

ETHOS SHALL expose each lane lifecycle and retirement operation from its owning
adapter module. Public CLI routing SHALL call that owner directly and SHALL NOT
reconstruct an equivalent Runtime graph in a forwarding facade.

#### Scenario: CLI invokes a lifecycle operation

- **WHEN** a lane refresh or retirement command resolves its implementation
- **THEN** it SHALL call the semantic owner directly
- **AND** no compatibility forwarding function, re-export, alias, service locator,
  or Runtime-composition factory SHALL remain.

#### Scenario: adapter behavior needs a test seam

- **WHEN** a test replaces one effectful dependency
- **THEN** it SHALL patch the semantic owner module directly
- **AND** production APIs SHALL NOT carry a Runtime object or runtime parameter.

#### Scenario: retirement reads lease state

- **WHEN** retirement evaluates current leases
- **THEN** it SHALL reuse the canonical repository status lease projection
- **AND** a second SQLite-only lease reader SHALL NOT remain.
