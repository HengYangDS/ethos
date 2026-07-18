## ADDED Requirements

### Requirement: Ordinary Work Lane retirement is fail-closed at effect time

ETHOS SHALL reobserve the selected linked Work Lane's registered path, branch
ref, checkout HEAD, and tracked/untracked status immediately before ordinary
landed or superseded retirement. It SHALL remove a verified-clean linked
worktree without `--force` before deleting its branch through an exact expected
head comparison. Any unavailable, stale, dirty, ambiguous, or failed
observation SHALL block ordinary retirement and preserve the target.

#### Scenario: linked lane becomes dirty after retirement planning

- **GIVEN** an owned linked Work Lane has a valid planned retirement observation
- **WHEN** uncommitted tracked or untracked content appears before the effect
- **THEN** ETHOS SHALL block ordinary retirement
- **AND THEN** it SHALL not remove the worktree, delete the ref, revoke its
  lease, or discard the uncommitted content.

#### Scenario: ref changes after worktree removal

- **GIVEN** a clean owned linked Work Lane passes immediate reobservation
- **WHEN** its branch ref no longer equals the requested head at deletion time
- **THEN** ETHOS SHALL report a blocked partial transition
- **AND THEN** it SHALL leave the newer ref intact for later inspection.

### Requirement: Unbound Work Lane refs require exceptional deletion admission

ETHOS SHALL NOT retire an unbound `work/*` ref through the ordinary retirement
command solely because no linked worktree is registered. It SHALL return a
machine-readable blocking gap that routes the target to a later
evidence-bound deletion-admission mechanism.

#### Scenario: local worktree registration is absent

- **GIVEN** a `work/*` ref is unbound from the current Git worktree registry
- **WHEN** an operator requests ordinary unbound retirement with a matching head
  and explicit reason
- **THEN** ETHOS SHALL preserve the ref and report that exceptional deletion
  admission is required.
