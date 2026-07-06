# repository-governance Delta

## MODIFIED Requirements

### Requirement: Accepted-root closeout leaves repository truth visible and clean

A successful accepted-root closeout MUST advance the accepted ref and synchronize
the accepted checkout worktree and index to the promoted candidate head.

#### Scenario: Closeout updates accepted worktree content

- **WHEN** `ethos land --closeout --apply` accepts a candidate head
- **THEN** the accepted branch, HEAD, index, and worktree all reflect the
  candidate head
- **AND** `git status --short` in the accepted checkout is empty

#### Scenario: Closeout worktree sync failure blocks success

- **WHEN** the accepted-ref compare-and-swap succeeds but the worktree sync fails
- **THEN** ETHOS reports `accepted_worktree_sync_failed` instead of
  `accepted_validated`
