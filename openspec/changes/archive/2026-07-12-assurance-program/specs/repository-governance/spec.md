## ADDED Requirements

### Requirement: Independent verification is an optional action-scoped adapter

ETHOS SHALL default independent verification to disabled and SHALL allow an
adopter to select optional or required depth for an individual transition
action without declaring provider identities in repository truth.

#### Scenario: A repository does not opt in

- **WHEN** no independent-verification policy is declared
- **THEN** ETHOS SHALL retain local-first readiness semantics
- **AND** SHALL NOT require a provider account, network, key, anchor, or receipt.

#### Scenario: Publish requires independent re-execution

- **WHEN** an adopter declares required independent verification for `publish`
- **THEN** `ethos publish` SHALL block without a valid exact receipt
- **AND** SHALL NOT make that policy an admission requirement for another action.

### Requirement: Receipts are exact bounded evidence

ETHOS SHALL admit an independent receipt only when its protected provider
configuration and signature validate and its remote, commit, tree, action,
proof floor, policy digest, and implementation digest match the request.

#### Scenario: Receipt is valid but not semantic proof

- **WHEN** an exact independent receipt is admitted
- **THEN** ETHOS SHALL project `independently_reexecuted`
- **AND** SHALL NOT claim semantic correctness or mint authority.

### Requirement: Reference adapter stays provider-local and constrained

The reference independent-identity adapter SHALL be one-shot and SHALL reject
foreign remotes, commits, arbitrary proof commands, unavailable sandboxing, and
receipt publication failure.

#### Scenario: Proof child process is created

- **WHEN** the adapter starts its independent proof command
- **THEN** it SHALL provide a minimal key-free environment
- **AND** SHALL use an out-of-tree runtime and checkout.
