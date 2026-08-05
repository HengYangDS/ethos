## ADDED Requirements

### Requirement: Accepted Specification Reconciliation

Accepted specifications SHALL describe only current implemented behavior and
SHALL NOT gain authority from an archived Change, migrated checklist, or stale
historical projection.

#### Scenario: An accepted requirement has no current executable owner

- **WHEN** reconciliation cannot map an accepted requirement to current source,
  tests, schemas, or a currently admitted external verifier
- **THEN** the requirement is removed, narrowed, or reported as a model gap
- **AND** historical wording is not retained merely because it once appeared in
  an archived Change.

#### Scenario: A migrated successor has not been implemented

- **WHEN** an archived source task maps an obligation to a successor outcome
- **THEN** the archive proves only lossless migration of that obligation
- **AND** the successor remains incomplete until its own Change is implemented,
  proved, archived, landed, and retired.

## REMOVED Requirements

### Requirement: Archived Work Lane candidate-drift continuation

**Reason**: Mandatory successor creation, rebasing, and topology-preserving merge
make retirement cost proportional to obsolete implementation history rather than
to unique surviving semantics.

**Migration**: Classify historical obligations against current accepted truth,
absorb only unique useful semantics through an owned atomic Change, prove current
or stronger implementations directly, and retire superseded or obsolete carriers
without replaying their code or Git ancestry.

## ADDED Requirements

### Requirement: Historical Work Lane semantic convergence

ETHOS SHALL preserve useful intent and unique semantics from a historical Work
Lane without requiring its obsolete implementation or Git ancestry to enter the
current terminal tree. Historical carriers remain immutable observations, not
mutation authority.

#### Scenario: Semantic refresh conflict fails closed

- **WHEN** the official candidate-base refresh encounters a semantic conflict
- **THEN** ETHOS MUST abort the replay and report `refresh_base_failed`
- **AND** it MUST restore the Work Lane branch and worktree to the expected clean
  head
- **AND** no manual rebase continue, skip, raw ref movement, or history
  replacement may be used to bypass the failure.

#### Scenario: Historical work is classified before implementation transfer

- **WHEN** a historical Work Lane is evaluated against current accepted truth
- **THEN** each useful obligation is classified as currently proved, uniquely
  valuable, superseded by stronger semantics, or obsolete
- **AND** only uniquely valuable semantics remain to be absorbed.

#### Scenario: Semantics are absorbed without replaying obsolete code

- **WHEN** current source and tests implement the historical lane's useful
  semantics exactly or more strongly
- **THEN** ETHOS records that semantic basis and permits exact retirement without
  rebasing or merging the historical implementation
- **AND** tree inequality alone does not imply missing product behavior.

#### Scenario: Historical implementation remains the best terminal form

- **WHEN** evidence shows that the historical implementation itself remains the
  shortest correct terminal form
- **THEN** an owned atomic Change may transfer that implementation onto the
  current candidate and regenerate HEAD-bound proof
- **AND** Git ancestry is preserved only when it carries necessary semantic or
  audit value, not as a universal retirement prerequisite.

#### Scenario: Historical facts are corrected without archive mutation

- **WHEN** independent replay or review corrects a fact recorded by the
  historical carrier
- **THEN** the active continuation MUST record a superseding correction with its
  reproducible inputs and digest
- **AND** the archived Change, historical Chronicle, and historical proof
  receipt MUST NOT be rewritten.
