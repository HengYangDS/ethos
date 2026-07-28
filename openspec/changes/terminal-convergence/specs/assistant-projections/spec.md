## MODIFIED Requirements

### Requirement: Projection Boundary
Collaboration and handoff SHALL be vendor-neutral projections over selected Commitments, fresh Facts, and Attestations; no host transcript or session state owns repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports package, registry, generator, and projection drift
  records without accepting host metadata as authority

#### Scenario: a different agent takes over
- **WHEN** an agent host changes
- **THEN** the successor consumes the same bounded handoff projection without replaying private session state

### Requirement: Terminal assistant projections are derived, not root configuration
Optional protocol adapters SHALL consume the kernel and remain replaceable; they SHALL not introduce a repository truth root.

#### Scenario: A repository is scaffolded or parity-checked

- **WHEN** ETHOS renders the current adopter scaffold or checks its manifest
- **THEN** `.ethos/assistants.toml` is absent from required artifacts
- **AND** assistant projection behavior continues to come from canonical source
  and activation contracts.

#### Scenario: The product removes the retired projection file

- **WHEN** the product checkout no longer contains `.ethos/assistants.toml`
- **THEN** projection checks and assistant tests remain valid
- **AND** no runtime consumer treats the removed file as required truth.

#### Scenario: a protocol adapter is removed
- **WHEN** a protocol adapter is uninstalled
- **THEN** the selected Commitment, Attestations, and other projections remain usable
