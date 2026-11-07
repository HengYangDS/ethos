## MODIFIED Requirements

### Requirement: Detached temporary worktree housekeeping is fail-closed

ETHOS SHALL inventory detached Git worktrees without treating detachment as
cleanup authority. It SHALL remove a worktree only after explicit authorization
when the entry is detached, clean, unlocked, below a controlled temporary root,
not the audited checkout, holds a `HEAD` that a retaining ref reaches, holds no
ignored file outside the regenerable roots, and is unchanged at immediate
reobservation. Retaining refs are heads, tags, remote-tracking refs and
`refs/keep/*`.

#### Scenario: Clean detached temporary worktree is removable

- **WHEN** `ethos lane housekeeping --json` observes a clean detached worktree
  below a controlled temporary root
- **THEN** it reports that exact path as removable without changing Git state
- **AND** removal occurs only with `--authorize --apply`.

#### Scenario: Valuable or active worktree remains protected

- **WHEN** a worktree is dirty, unreadable, branch-bound, Git-locked, outside
  controlled temporary roots, or is the audited checkout, or holds a `HEAD` that
  no retaining ref reaches or whose reachability Git cannot report, or holds
  ignored files outside a root `.venv`, a root `node_modules` and bytecode beside
  its source
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
