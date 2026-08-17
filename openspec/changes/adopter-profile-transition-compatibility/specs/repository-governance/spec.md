## ADDED Requirements

### Requirement: Adopter reader compatibility is bounded and non-authorizing

ETHOS SHALL preserve read-only access to explicitly enumerated deployed adopter
declaration shapes without restoring retired mutation semantics. Compatibility
projections SHALL validate exact fields and values, bind original carrier
bytes, and remain ineligible for proof, Lease, or Git-effect authority.

#### Scenario: Deployed branch-role transition declaration is inspected

- **WHEN** a repository profile contains the exact deployed
  `[[branch_roles.transitions]]` row
- **THEN** `status` SHALL validate the complete row shape and read the current
  branch-role policy
- **AND** the transition row SHALL NOT enter the current `BranchRolePolicy` or
  mint mutation authority
- **AND** strict mutation parsing SHALL continue to reject the retired row.

#### Scenario: Terminal-v1 repository Commitment is planned

- **WHEN** read-only `plan` observes the exact terminal-v1 repository
  Commitment shape
- **THEN** it SHALL return the schema-v1 semantic projection, original carrier
  SHA-256, and legacy semantic digest
- **AND** it SHALL explicitly report that proof and mutation authority are
  false
- **AND** it SHALL NOT emit a schema-v2 `TransitionPlan`.

#### Scenario: Compatibility declaration drifts

- **WHEN** a transition row or terminal-v1 Commitment contains an unknown field
  or malformed value
- **THEN** the reader SHALL return a stable structured gap without traceback
- **AND** it SHALL NOT silently discard or reinterpret the drift.

### Requirement: Package-only runtime proves deployed adopter reader shapes

The package acceptance gate SHALL exercise deployed adopter profile and
Commitment shapes through a fresh wheel-installed binary without importing the
ETHOS source checkout or an external governance product.

#### Scenario: Source-hidden adopter readers execute

- **WHEN** local-install smoke creates an adopter with the deployed transition
  declaration and terminal-v1 repository Commitment
- **THEN** the installed package SHALL return passing JSON for `status` and
  read-only `plan`
- **AND** the plan SHALL carry exact non-authorizing compatibility metadata
- **AND** no traceback, v2 proof authority, or repository mutation SHALL occur.
