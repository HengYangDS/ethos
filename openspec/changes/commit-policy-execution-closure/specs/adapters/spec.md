## ADDED Requirements

### Requirement: Git and Forge commit-policy transports remain thin

The installed `commit-msg` and `pre-push` hooks and native GitHub and GitLab CI
projections SHALL transport exact Git coordinates into the same package-runtime
commit-policy admission owner. No transport SHALL parse the subject expression,
walk a distinct revision range, keep policy state, or define provider-local
exceptions.

#### Scenario: Hook installation converges the complete launcher set

- **WHEN** `ethos hook install` activates a package runtime
- **THEN** the immutable generation contains exact launchers for `commit-msg`,
  `pre-commit`, `pre-push`, and `reference-transaction`
- **AND** activation, rollback, cleanup, and status treat that set as one
  generation rather than modifying a current generation in place.

#### Scenario: Pre-push receives several updates

- **WHEN** Git supplies multiple branch or tag update records on standard input
- **THEN** the hook evaluates every non-delete update independently through the
  shared range owner and blocks if any report is non-passing
- **AND** delete records do not create a fictitious commit range.

#### Scenario: Local pre-push is bypassed

- **WHEN** a contributor invokes `git push --no-verify`
- **THEN** GitHub and GitLab CI invoke the public commit-range admission command
  over their exact integration event coordinates
- **AND** neither provider carries a copied regular expression, range walker, or
  commit-policy state machine.

#### Scenario: Provider event is not an integration event

- **WHEN** a manually dispatched or observational workflow has no exact base and
  proposed commit pair
- **THEN** the provider does not fabricate commit-range success
- **AND** other repository gates may run without claiming integration-range
  enforcement for that event.

#### Scenario: Configured identity policy is enabled

- **WHEN** the repository independently enables configured author and committer
  identity checks
- **THEN** identity validation consumes the introduced commit sequence already
  derived by the commit-range owner
- **AND** it owns no second range derivation helper.
