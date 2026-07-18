## ADDED Requirements

### Requirement: Maintainer remote reconciliation preserves observed protected history

For a maintainer-authorized reconciliation of divergent protected repository
refs, ETHOS operations SHALL retain each fresh observed remote tip as an
ancestor of the proposed reconciliation head, use ordinary merge commits for
history integration, and keep local proof, remote ref mutation, and hosted
provider observation as distinct evidence classes.

#### Scenario: protected refs are divergent before reconciliation

- **WHEN** a maintained repository observes different protected `dev` or `main` tips across its configured forge providers
- **THEN** the reconciliation Lane records the exact observed tips before mutation
- **AND** it creates a claim-bound carrier that names the scope, fallback, and kill signal
- **AND** its proposed reconciliation head remains a descendant of every recorded tip

#### Scenario: local proof precedes protected remote update

- **WHEN** the reconciliation head has passed its required local proof and governed local closeout
- **THEN** each protected remote update is first tested with its own ordinary push dry-run
- **AND** no force update, rebase, reset-based ref movement, or stash-based conflict bypass is used
- **AND** later remote and hosted-provider observations are recorded without treating local proof as either result
