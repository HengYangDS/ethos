## ADDED Requirements

### Requirement: Lifecycle commit objects inherit repository signing policy

ETHOS SHALL create direct lifecycle commit objects through one owner that
inherits the repository's effective commit-signing policy and verifies any
required signature before a ref or Lease effect.

#### Scenario: Signing is enabled and trusted

- **WHEN** a lifecycle operation creates a commit object in a repository whose
  effective `commit.gpgsign` is enabled
- **THEN** the object is signed with the bound configured signer
- **AND** external trust verification passes before any ref mutation.

#### Scenario: Signing is disabled

- **WHEN** effective `commit.gpgsign` is disabled or absent
- **THEN** the lifecycle object may remain unsigned
- **AND** ETHOS does not invent a repository-independent signing requirement.

#### Scenario: Required signature is not trusted

- **WHEN** signing is enabled but object creation or external trust verification
  fails
- **THEN** the lifecycle operation reports the typed signing gap
- **AND** no ref, Lease, or worktree effect remains.

### Requirement: Identity repair supports one receipt-bound linear suffix

ETHOS SHALL extend the existing public identity-repair capability to recreate a
bounded linear suffix under current signing policy and apply the resulting ref
mapping through one exact-CAS receipt.

#### Scenario: Exact suffix is derived

- **WHEN** the current owner supplies one exclusive base for a clean linear
  suffix containing the Work Lane and local integration-train heads
- **THEN** derive creates and verifies the ordered replacement commits
- **AND** returns an immutable receipt containing every old/new commit and ref
  coordinate plus the exact apply command.

#### Scenario: Exact receipt applies

- **WHEN** holder, Lease generation, old heads, trees, worktrees, commit payloads,
  and receipt digest remain unchanged
- **THEN** apply advances only the receipt-declared Work Lane and integration
  refs, synchronizes their worktrees, and advances the existing Lease
- **AND** a retry can recognize and complete the same operation.

#### Scenario: Suffix is not a pure identity and parent repair

- **WHEN** the range contains a merge, a tree/message/author/committer change,
  an untrusted replacement, or a moved coordinate
- **THEN** derive or apply fails closed with a typed gap
- **AND** no general history rewrite is authorized.
