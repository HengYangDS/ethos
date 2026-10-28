# Proposal

## Why

Host-store retention writes into repositories it only observes. Since the unreleased
retention-selection-window fix, retention takes each recorded consumer's selection lock without
blocking before it reads the consumer's `CURRENT` and `ROLLBACK`. Taking a filelock creates its
parent directory and its lock file when they are absent, so retention creates
`ethos/runtime-selection.lock` in every recorded repository that has no ETHOS state.

- A recorded repository can lose its ETHOS state while its common directory remains: its `ethos/`
  directory was removed, or another repository took its path. Retention then releases the record,
  because nothing selects the installation, and leaves the created lock behind in a repository that
  ETHOS no longer governs.
- The distribution specification requires installation, upgrade, rollback and uninstall to use exact
  owned resources and fresh live-consumer observations. An observation that creates state in the
  observed repository does neither.
- No release carries the write: 0.2.0-alpha.17 did not take the consumer's lock, and the fix that
  added it is still under `[Unreleased]`.

## What Changes

- Retention takes a consumer's selection lock only when the consumer's `ethos/` directory exists.
  Without it, the consumer has no selectors and no selection in progress, so retention reads the
  absent selectors directly, releases the record and creates nothing.
- The `[Unreleased]` fix note in `CHANGELOG.md` states that retention creates nothing in a
  repository without ETHOS state.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `distribution`: the requirement "Installed product migration preserves live consumers" gains a
  scenario in which reclamation observes a recorded repository without ETHOS state.

## Impact

- Code: `src/ethos/adapters/repo/runtime/materialization/host_retention.py`; tests in
  `tests/unit/adapters/repo/runtime/materialization/test_host_retention.py`.
- A repository with ETHOS state is observed exactly as before, including through its held lock.
- `python_product` grows by at most 2 lines.
