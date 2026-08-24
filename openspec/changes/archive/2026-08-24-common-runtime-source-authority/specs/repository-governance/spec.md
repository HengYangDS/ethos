## MODIFIED Requirements

### Requirement: Git-common hook runtime activation is singular

ETHOS SHALL maintain one effective hook/runtime activation and one expected
runtime source identity per Git common directory. The invoking repository
authority SHALL select that identity once. Linked worktrees SHALL validate the
common projection against it without interpreting their own historical profile
as another identity authority.

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

#### Scenario: Historical linked checkout cannot veto current activation

- **GIVEN** the invoking repository resolves a valid accepted runtime source
  identity
- **AND** a linked historical checkout contains an obsolete or invalid profile
- **WHEN** `ethos hook install --root <invoking-repository> --json` runs
- **THEN** every linked worktree validates the same common activation against
  the invoking repository's exact source identity
- **AND** the historical profile does not select or veto that identity
- **AND** unreadable Git configuration or runtime projection still fails closed.
