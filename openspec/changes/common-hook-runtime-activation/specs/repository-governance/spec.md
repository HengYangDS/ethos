## ADDED Requirements

### Requirement: Git-common hook runtime activation is singular
ETHOS SHALL maintain one effective hook/runtime activation per Git common
directory, and every linked worktree SHALL resolve that same activation without
retaining a parallel worktree-local authority.

#### Scenario: One install converges all linked worktrees
- **GIVEN** linked worktrees currently resolve different generated hook
  generations
- **WHEN** `ethos hook install --root <any-linked-worktree> --json` succeeds
- **THEN** the Git common directory owns one effective `core.hooksPath`
- **AND** every linked worktree resolves the same current runtime source identity
- **AND** stale worktree-local activation overrides are absent

#### Scenario: Cleanup preserves active generations
- **WHEN** hook/runtime cleanup evaluates generated generations
- **THEN** it removes only generations with no effective config, launcher,
  process, or operation consumer
- **AND** it reports the precise retained and removed generations
- **AND** an unknown consumer blocks deletion.
