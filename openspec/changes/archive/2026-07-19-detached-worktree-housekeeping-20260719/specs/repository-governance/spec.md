## MODIFIED Requirements

### Requirement: Detached temporary worktree housekeeping is fail-closed

ETHOS SHALL inventory detached Git worktrees without treating detachment as
cleanup authority. It SHALL remove a worktree only after explicit authorization
when the entry is detached, clean, unlocked, below a controlled temporary root,
not the audited checkout, and unchanged at immediate reobservation.

#### Scenario: Clean detached temporary worktree is removable

- **WHEN** `ethos lane housekeeping --json` observes a clean detached worktree
  below a controlled temporary root
- **THEN** it reports that exact path as removable without changing Git state
- **AND** removal occurs only with `--authorize --apply`.

#### Scenario: Valuable or active worktree remains protected

- **WHEN** a worktree is dirty, unreadable, branch-bound, Git-locked, outside
  controlled temporary roots, or is the audited checkout
- **THEN** housekeeping reports a machine-readable protection reason
- **AND** it does not remove the worktree even in authorized apply mode.

#### Scenario: Candidate changes before removal

- **WHEN** a planned removable worktree changes before the effect
- **THEN** ETHOS reports a stale-candidate gap
- **AND** it preserves the changed worktree.

#### Scenario: Git inventory is unavailable

- **WHEN** Git cannot return the registered worktree inventory
- **THEN** housekeeping reports a blocking inventory gap
- **AND** it does not project an empty removable set as successful inspection.
