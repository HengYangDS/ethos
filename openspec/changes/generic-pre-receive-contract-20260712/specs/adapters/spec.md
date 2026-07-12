## MODIFIED Requirements

### Requirement: Bounded External Evidence Adapters

ETHOS SHALL verify external identity assertions, hosted-enforcement receipts,
and control-replacement verifier receipts only when the applicable Commitment
requires them. Adapters SHALL store no credentials and SHALL NOT mint
authority. Optional provider-local reference implementations SHALL live in a
declared extension bundle, never in an unowned root-level adapter directory.

#### Scenario: Generic Git server enforcement is disabled by default

- **WHEN** a provider has not installed the generic Git pre-receive adapter or
  its protected provider-local configuration selects `disabled`
- **THEN** ordinary ETHOS adoption, status, plan, prove, land, and local
  publication readiness require no account, key, receipt store, daemon, network
  service, or `yheng-agent-ethos` user
- **AND** the adapter does not mint authority or alter product lifecycle truth.

#### Scenario: A protected generic Git update has an exact independent receipt

- **WHEN** a provider-enabled generic Git pre-receive adapter receives a
  non-deletion update for a configured protected ref
- **THEN** it accepts the update only when its provider-store receipt has a
  valid protected-anchor signature and exactly binds the configured remote,
  proposed commit, proposed tree, action, proof-floor ID/digest, gate-policy
  digest, and verifier implementation digest
- **AND** it rejects absent, stale, failed, malformed, unsigned, or mismatched
  receipts before Git accepts the ref.

#### Scenario: An update is outside the configured protected set

- **WHEN** a generic Git pre-receive adapter receives an update for a ref not
  named by its provider-local protected-ref configuration
- **THEN** it does not require a receipt for that ref
- **AND** it does not execute a client-supplied command or infer policy from the
  proposed tree.

#### Scenario: The server adapter remains a thin physical extension

- **WHEN** ETHOS ships the generic Git pre-receive reference adapter
- **THEN** its source, manifest, documentation, and focused tests reside under
  `extensions/independent-verification/adapters/generic_git/` or that extension
  bundle's colocated test surface
- **AND** no root-level `reference_adapters/` source, forwarding module, or
  compatibility alias exists
- **AND** GitHub and GitLab adapters remain projections over the same receipt
  contract rather than separate governance kernels.
