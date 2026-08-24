## ADDED Requirements

### Requirement: Git-common hook runtime activation is singular

ETHOS SHALL maintain one effective hook/runtime activation per Git common
directory. A linked worktree SHALL NOT retain a parallel worktree-local
activation owner.

#### Scenario: One install converges all linked worktrees

- **GIVEN** linked worktrees resolve different generated hook generations
- **WHEN** `ethos hook install --root <any-linked-worktree> --json` succeeds
- **THEN** repository-common Git config owns the effective `core.hooksPath`
- **AND** every linked worktree resolves the same current runtime source identity
- **AND** owned worktree-local activation overrides are absent.

#### Scenario: Cleanup preserves every observed consumer

- **WHEN** hook/runtime cleanup evaluates generated generations
- **THEN** it removes only generations absent from effective config, launchers,
  live process commands, and in-flight operation records
- **AND** it reports exact retained and removed paths
- **AND** an unreadable consumer source blocks deletion.
