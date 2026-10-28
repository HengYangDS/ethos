# Design

## Context

See [proposal.md](proposal.md).

- **Consumer records.** `pin_installed_runtime` records the repository's common directory in the
  installation under the host store's `install.lock` and returns. The caller names the installation
  later, outside that lock: in `CURRENT` through `activate_runtime`, and for a preserved predecessor
  in `ROLLBACK` through `_hold_rollback`.
- **Retention.** `retire_unused_installations` runs under `install.lock` after every hook
  installation. For each record it reads the consumer's `CURRENT` and `ROLLBACK`. A consumer that
  names the installation in neither is released and its record unlinked. An installation without
  records and without an operational reference is removed.
- **The window.** Between the record and the selector write, the repository names the installation
  nowhere, so a concurrent retention releases it. Nothing records it again, so a later retention can
  remove the installation that its `CURRENT` names.
- **The selection lock.** Each repository already has one selection lock,
  `ethos/runtime-selection.lock` in its common directory, which every selector effect takes with a
  10 s bound.

## Goals / Non-Goals

**Goals:**

- Retention never releases a consumer that may be about to name the installation.
- A repository's selection holds its lock for the whole window, whichever command performs it.

**Non-Goals:**

- Retiring installations through a rename first. With the window closed, no selected installation is
  retired, so no reader of a selected runtime observes its deletion.
- Making runtime selection gaps carry their triggering observation. That rule applies to every gap
  and needs its own design review.
- Changing repositories that run an earlier release.

## Decisions

- **The existing selection lock marks a selection in progress.** Hook installation holds it from the
  `CURRENT` read before its pins until `_hold_rollback`; adoption holds it across materialization and
  `activate_runtime`. The lock file is created with its directory, so a repository holds its lock
  before its first record exists.
- **Retention never waits.** It already holds `install.lock`. It acquires each consumer's selection
  lock without blocking and reads the selectors under it. A held lock raises `Timeout`, an `OSError`,
  which retention already reports as unknown: the record and the installation stay, and a later
  retention decides once the selection has settled. A selection waits for `install.lock` while it
  holds its own lock, and retention never blocks on a selection lock, so the two locks form no cycle.
- **Unknown, not needed.** A selection in progress has named nothing yet, so retention reports what
  it observes, unknown liveness, which the specification already treats as preventing deletion.
- **One lock object per repository.** `runtime_selection_lock` returns a filelock singleton keyed on
  the resolved common directory. `activate_runtime`, `restore_runtime_selection` and
  `runtime_selection_transaction` take it inside the held window and re-enter it in the same thread;
  another thread or process still waits.
- **The changelog entry stays under `[Unreleased]`.** The distribution specification keeps upcoming
  changes there until release preparation selects them, so a separate release Change refreshes the
  prepared 0.2.0-alpha.18 entry at the landed head.
- **Rejected: holding `install.lock` through activation.** Pins in every other repository would then
  wait for a whole activation, beyond their 10 s bound.
- **Rejected: recording the consumer again after selection.** A retention inside the window could
  still remove the installation before the selector write.

## Risks / Trade-offs

- [A second selector effect in the same repository arrives during a selection that pins supply] → It
  waits up to the existing 10 s bound and then fails explicitly; before, it interleaved and failed on
  a stale `CURRENT`. The hold covers verification, sealing, launcher materialization and the selector
  writes of one repository.
- [A repository still runs an earlier release] → Its activations and retentions keep the old window
  until it rebinds; the release notes name this.
- [A consumer's common directory is not writable] → Creating its lock fails with `OSError`, so
  retention reports unknown and keeps the installation, as for an unreadable selector.
- [A repository's `ethos/` directory is a symbolic link] → Taking the lock creates its empty file
  through the link before the selection checks refuse the link; no selection changes.
