## MODIFIED Requirements

### Requirement: Bounded External Evidence Adapters

ETHOS SHALL verify external identity assertions, hosted-enforcement receipts,
and control-replacement verifier receipts only when the applicable Commitment
requires them. Adapters SHALL store no credentials and SHALL NOT mint
authority. Provider-local verifier and Git-hook executables SHALL be supplied
and governed by the operator outside the ETHOS product source and distribution
surface while conforming to the provider-neutral receipt contract.

#### Scenario: control replacement uses protected bootstrap evidence

- **WHEN** a candidate changes admission, proof floors, schemas, hooks,
  identity trust, enforcement adapters, or declarative controls
- **THEN** closeout requires a receipt outside the candidate tree binding both
  heads, both control digests, verifier digest, candidate proof, and bootstrap
  Chronicle decision
- **AND** the candidate proof is a native executed `ethos prove --execute --json`
  result with `command = "prove"`, `ok = true`, `state = "proven"`,
  `data.executed = true`, and matching candidate HEAD bindings in
  `data.evidence.head` and `data.provenance.predicate.head`
- **AND** a hand-authored `{head, state}` envelope is not accepted as candidate
  proof
- **AND** missing or unverifiable provenance returns `defer`.

#### Scenario: hosted prevention requires exact receipt

- **WHEN** ETHOS claims hosted prevention for a ref transition
- **THEN** a provider receipt binds the exact action, resource, old value, new
  value, observation, coverage, and receipt digest
- **AND** local hooks or provider configuration alone do not prove prevention.

#### Scenario: provider-local implementation is operator supplied

- **WHEN** an operator enables independent verification or generic Git
  pre-receive enforcement
- **THEN** the executable implementation resides outside the ETHOS product
  source and distribution surface
- **AND** it consumes the published provider-neutral receipt contract without
  creating product policy, credentials, accounts, network services, daemons, or
  scheduling requirements.

#### Scenario: Generic Git server enforcement is disabled by default

- **WHEN** a provider has not installed a conforming generic Git pre-receive
  adapter or its protected provider-local configuration selects `disabled`
- **THEN** ordinary ETHOS adoption, status, plan, prove, land, and local
  publication readiness require no account, key, receipt store, daemon, network
  service, or named service user
- **AND** the adapter does not mint authority or alter product lifecycle truth.

#### Scenario: A protected generic Git update has an exact independent receipt

- **WHEN** a provider-enabled conforming pre-receive adapter receives a
  non-deletion update for a configured protected ref
- **THEN** it accepts the update only when its provider-store receipt has a
  valid protected-anchor signature and exactly binds the configured remote,
  proposed commit, proposed tree, action, proof-floor ID/digest, gate-policy
  digest, and verifier implementation digest
- **AND** it rejects absent, stale, failed, malformed, unsigned, or mismatched
  receipts before Git accepts the ref.

#### Scenario: An update is outside the configured protected set

- **WHEN** a conforming generic Git pre-receive adapter receives an update for a
  ref not named by its provider-local protected-ref configuration
- **THEN** it does not require a receipt for that ref
- **AND** it does not execute a client-supplied command or infer policy from the
  proposed tree.

#### Scenario: Provider implementations share one contract

- **WHEN** GitHub, GitLab, independent-identity, or generic Git providers project
  external enforcement
- **THEN** they conform to the same receipt and decision contract
- **AND** no provider executable becomes a second governance kernel or a
  required ETHOS distribution asset.
