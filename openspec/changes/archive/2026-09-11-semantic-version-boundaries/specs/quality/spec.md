## ADDED Requirements

### Requirement: Version metadata has an effective interpretation owner

ETHOS SHALL enforce necessary version boundaries through their owning readers.
A portable gate declaration SHALL accept only its supported format. Executable
policy shipped inside one immutable package SHALL share that package identity;
unused native configuration labels SHALL be removed instead of given artificial
validators solely to justify their presence.

#### Scenario: Unsupported gate declaration is supplied

- **WHEN** a gate registry declares an unsupported or malformed version
- **THEN** the native loader rejects it before any gate executes
- **AND** the supported declaration still produces its original dependency graph

#### Scenario: Native configuration label has no interpretation consumer

- **WHEN** a version label does not affect native parsing, interpretation or compatibility
- **THEN** removing it preserves the relevant native behavior
- **AND** tool release versions, package locks and integrity digests remain intact

#### Scenario: Package-local policy has one identity

- **WHEN** topology policy is loaded from its immutable package
- **THEN** no independent policy version can override the interpreting package
- **AND** malformed policy and checkout overrides remain rejected

### Requirement: Python visibility follows semantic ownership

ETHOS SHALL enforce private-module and private-symbol ownership across every
governed Python consumer. Import spelling and aliases SHALL NOT widen access.
A shared public operation SHALL expose a real consumer capability rather than
rename internal coupling. Tool coverage claims SHALL match exercised behavior.

#### Scenario: Private module crosses an owner boundary

- **WHEN** a consumer outside the private module's immediate semantic package imports it
- **THEN** the existing layout gate rejects the dependency for either import spelling
- **AND** legitimate direct package-internal consumers remain allowed

#### Scenario: Private symbol crosses a module boundary

- **WHEN** another module imports a private symbol, including an aliased or relative import
- **THEN** the existing visibility owner reports the defining and consuming modules
- **AND** protocol dunder names are not mistaken for private implementation names

#### Scenario: Resource defaults are interpreter-owned

- **WHEN** a caller changes CWD or supplies an incompatible adopter-local schema
- **THEN** native default gates and skill schema meaning remain bound to their interpreter
- **AND** an explicit missing gate declaration fails instead of choosing a fallback
