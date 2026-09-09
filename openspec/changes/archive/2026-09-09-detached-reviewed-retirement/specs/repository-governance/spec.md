## ADDED Requirements

### Requirement: Reviewed retirement derives only existing native resources

ETHOS SHALL allow existing reviewed-content abandonment to select one registered
detached worktree by exact absolute path. Its immutable receipt SHALL bind the
literal target, native Git registration, detached HEAD, index and content,
accepted object and actor. An absent branch SHALL produce no ref-deletion or
Lease effect. Existing coordinated quiescence, admission, native removal and
monotonic recovery SHALL remain the single protocol.

#### Scenario: Reviewed detached content retires without synthetic authority

- **WHEN** the operator selects a registered detached worktree by absolute path
  and explicitly reviews its final content after actual writers have stopped
- **THEN** ETHOS derives only the exact worktree-removal effect
- **AND** application removes that worktree and registration while preserving
  all refs, Lease rows and other worktrees, including same-HEAD siblings.

#### Scenario: Changed native identity or consumption prevents removal

- **WHEN** the selected path is aliased, reattached, locked, replaced, actively
  consumed, incompletely observable, or differs from the reviewed HEAD, native
  registration, content or index
- **THEN** ETHOS rejects the effect and retains current content
- **AND** changed actor or accepted coordinates also prevent application.

#### Scenario: Detached removal resumes through the same receipt

- **WHEN** a detached retirement is interrupted before native deregistration
  or after its removal is complete
- **THEN** recovery reobserves the same bound resources and executes only
  remaining effects
- **AND** it never deletes replacement bytes, recreates a branch or Lease, or
  replays a completed native removal.
