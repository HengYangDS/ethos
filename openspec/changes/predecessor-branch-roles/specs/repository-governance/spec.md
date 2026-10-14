## ADDED Requirements

### Requirement: Predecessor branch-role tables keep their incumbent meaning

ETHOS SHALL read an incumbent branch-role table that lacks `canonical_sibling_worktrees`, or lacks both that field and `release_mirror`, with the predecessor defaults of no canonical sibling worktrees and an independent release mirror when it selects accepted closeout or lease control roles, and SHALL reject every other incomplete or unknown table.

#### Scenario: A five-field incumbent table governs closeout

- **WHEN** the accepted head declares only the release, accepted and candidate branches and the work and proposal prefixes
- **THEN** closeout reads those roles with an independent release mirror and no canonical sibling worktrees
- **AND** the candidate's own table does not decide the incumbent roles

#### Scenario: Another incomplete table stays unavailable

- **WHEN** the incumbent table omits any other field, or omits `release_mirror` while declaring `canonical_sibling_worktrees`
- **THEN** closeout reports `accepted_policy_unavailable`

### Requirement: Unclassified ref moves fail with an explicit reason

ETHOS SHALL reject a candidate-integration ref move whose ref matches no declared branch role with `ref_transition_operation_unresolved:<ref>`, and SHALL leave that ref unmoved.

#### Scenario: A candidate integration targets an undeclared ref

- **WHEN** a landing integrates a proven Work Lane into a candidate branch that matches no resolved role
- **THEN** the candidate update fails with `ref_transition_operation_unresolved` naming that ref
- **AND** the candidate branch does not move
