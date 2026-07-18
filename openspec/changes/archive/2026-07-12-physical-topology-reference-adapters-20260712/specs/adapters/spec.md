# adapters Delta

## MODIFIED Requirements

### Requirement: Bounded External Evidence Adapters

ETHOS SHALL verify external identity assertions, hosted-enforcement receipts,
and control-replacement verifier receipts only when the applicable Commitment
requires them. Adapters SHALL store no credentials and SHALL NOT mint
authority. Optional provider-local reference implementations SHALL live in a
declared extension bundle, never in an unowned root-level adapter directory.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires a receipt outside the candidate tree binding both
  heads, both control digests, verifier digest, candidate proof, and bootstrap
  Chronicle decision
- **AND** missing or unverifiable provenance returns `defer`.

#### Scenario: hosted prevention requires exact receipt

- **WHEN** ETHOS claims hosted prevention for a ref transition
- **THEN** a provider receipt binds the exact action, resource, old value, new
  value, observation, coverage, and receipt digest
- **AND** local hooks or provider configuration alone do not prove prevention.

#### Scenario: provider-local reference implementation is physically bounded

- **WHEN** ETHOS ships the default-off independent-verification reference source
- **THEN** it resides at
  `extensions/independent-verification/adapters/independent_identity/reference_verifier.py`
- **AND** its manifest, documentation, and focused tests are colocated in that
  extension bundle
- **AND** no root-level `reference_adapters/` source, forwarding module, or
  compatibility alias remains
- **AND** the extension does not create an adopter policy, account, key,
  network, daemon, or scheduling requirement.
