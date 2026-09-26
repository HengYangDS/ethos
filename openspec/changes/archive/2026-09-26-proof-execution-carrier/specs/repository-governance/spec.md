## ADDED Requirements

### Requirement: Proof execution carrier is not proof authority

An exact-head repository proof MAY run gates in a separately selected clean
worktree. The authoring Work Lane SHALL remain the authority for actor, Lease,
committed intent and proof issuance. The execution carrier SHALL use the same
Git common directory, be detached at that exact commit and have an unchanged
index and tracked/untracked source corresponding to its HEAD.

#### Scenario: A staged archive needs a current-policy proof

- **WHEN** a Work Lane has a reviewed official archive staged and its unchanged
  HEAD requires new quality checks
- **AND** the caller selects a clean, same-common-dir carrier at that HEAD
- **THEN** ETHOS executes the current required checks against the carrier
- **AND** a passing Attestation binds the original lane's intent, HEAD and Lease
- **AND** the original staged and working bytes remain unchanged.

#### Scenario: The carrier is not the exact committed source

- **WHEN** the selected carrier is foreign, attached to another branch, dirty,
  at another commit, or changes during execution
- **THEN** ETHOS rejects or reports an unknown outcome without a passing proof
- **AND** it neither edits the authoring lane nor treats the carrier's Lease as
  permission.

#### Scenario: The requested exact HEAD is stale

- **WHEN** `--expect-head` differs from the authoring lane's current HEAD
- **THEN** ETHOS rejects before executing carrier gates
- **AND** it preserves the original staged archive and issues no proof.

### Requirement: Carrier proof preserves independent admission boundaries

The proof policy SHALL be selected from the committed source and evaluated at
the current required floor. Earlier policy results, carrier cleanliness,
repository identity, valid Lease and successful checks are independent claims;
none substitutes for another. The ordinary clean-lane proof path SHALL not
require an execution carrier.

#### Scenario: Authority or staged content changes during checks

- **WHEN** the authoring lane's HEAD, Lease generation, staged index or working
  content changes before issuance
- **THEN** ETHOS does not mint a passing Attestation from completed gates
- **AND** it preserves the exact completed-check diagnostics for recovery.

#### Scenario: Historical proof cannot meet a stronger current floor

- **WHEN** previous check materials do not prove each currently required
  quality subject
- **THEN** ETHOS requires execution of the missing current checks
- **AND** it does not re-sign the historical proof or weaken the policy.
