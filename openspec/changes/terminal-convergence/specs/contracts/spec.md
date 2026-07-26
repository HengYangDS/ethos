## ADDED Requirements

### Requirement: Language-neutral Terminal Contracts
ChangeContract, Attestation, RepositoryFacts, PlanIR, permission, adapter, and pack contracts MUST have language-neutral schemas and strict Python bindings without duplicate model owners.

#### Scenario: A non-Python adopter consumes a plan
- **WHEN** it validates a PlanIR instance against the published schema
- **THEN** it can interpret node identity, dependencies, verdicts, permissions, and artifact references without importing Python code

### Requirement: Vendor-neutral Actor Reference
Actor references MUST use the opaque four-segment form `kind:namespace:instance-kind:id`; the kernel MUST validate structure and equality only and MUST NOT enumerate vendors or infer privilege from names.

#### Scenario: A new agent vendor participates
- **WHEN** it supplies a structurally valid actor reference and explicit permissions
- **THEN** the same lifecycle and authority checks apply without a kernel code change

### Requirement: Immutable Intent Amendment
A ChangeContract MUST remain immutable and effective intent MUST be derived by folding ordered, digest-bound amendment attestations.

#### Scenario: A session is lost after intent changes
- **WHEN** another actor takes over with the base contract and amendment attestations
- **THEN** it reconstructs the same effective intent without the original transcript

### Requirement: Singular Active Change Carrier
Each active OpenSpec Change MUST use `contract.toml` as the sole ETHOS-owned
carrier for repository subject, intent, and material scope. Claims, Chronicle,
and `scope.toml` MUST NOT participate in the current lifecycle verdict.

#### Scenario: A material path is evaluated
- **WHEN** `lane prewrite`, changed planning, or proof selects an active Change
- **THEN** all three surfaces evaluate the same strict `ChangeContract.scope`
- **AND** malformed or historical parallel carriers grant no authority
