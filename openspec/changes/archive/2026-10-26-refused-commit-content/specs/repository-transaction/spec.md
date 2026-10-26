## MODIFIED Requirements

### Requirement: Rejected raw Git transitions fail cleanly or explicitly

The hook SHALL compensate an already projected index/worktree only from an exactly proven target projection of a commit that another ref already contains, and SHALL never guess across an unrelated overlay or discard content that only the rejected operation committed.

#### Scenario: A clean protected checkout is projected before rejection

- **WHEN** Git leaves HEAD unchanged, index/worktree exactly equal the rejected target tree, and another ref contains the target
- **THEN** the hook restores the exact current HEAD tree and verifies the restoration

#### Scenario: A rejected commit holds the caller's own content

- **WHEN** no other ref contains the rejected target, as for a direct commit to a protected branch
- **THEN** compensation is refused and the index and worktree stay unchanged
- **AND** the refusal names the rejected commit

#### Scenario: The index or worktree contains another overlay

- **WHEN** exact projection ownership cannot be proven
- **THEN** compensation is refused
- **AND** no unrelated staged or unstaged content is silently discarded
