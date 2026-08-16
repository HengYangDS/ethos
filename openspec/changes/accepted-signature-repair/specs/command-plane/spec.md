## MODIFIED Requirements

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

#### Scenario: Exact receipt dry-run is ready

- **WHEN** holder, Lease generation, old heads, trees, worktrees, commit payloads,
  and receipt digest remain unchanged
- **AND** the receipt is evaluated without apply
- **THEN** the public result reports `verdict=pass` and
  `state=ready_to_repair_identity`
- **AND** no ref, Lease, or worktree mutation occurs.

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
