## ADDED Requirements

### Requirement: Opt-in accepted-to-release fast-forward mirror

ETHOS SHALL support `branch_roles.release_mirror = "accepted_ff"` as an
opt-in policy that makes the configured release branch advance only with an
official accepted closeout to the exact proven candidate head.

#### Scenario: Official closeout mirrors both refs atomically

- **WHEN** the candidate head is proven, the release branch is an ancestor of
  accepted truth, and `release_mirror` is `accepted_ff`
- **THEN** ETHOS SHALL compare-and-swap accepted and release refs in one Git
  ref transaction to the candidate head
- **AND** it SHALL bind an exact one-shot closeout intent to each protected ref
- **AND** it SHALL leave both refs unchanged if the transaction is rejected.

#### Scenario: Raw release move is rejected

- **WHEN** a release ref move occurs outside official closeout while the
  candidate committed policy enables `accepted_ff`
- **THEN** admission SHALL require candidate topology, executed proof, and the
  exact release closeout intent
- **AND** it SHALL report a release-mirror structured gap when that intent is
  absent or invalid.

#### Scenario: Linked release worktree is synchronized

- **WHEN** an enabled release mirror has a linked worktree after a successful
  closeout transaction
- **THEN** ETHOS SHALL reset that worktree to the promoted candidate head and
  verify it is clean
- **AND** it SHALL report a structured failure instead of masking an unsafe
  synchronization result.
