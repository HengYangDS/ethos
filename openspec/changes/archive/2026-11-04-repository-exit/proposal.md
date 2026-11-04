# Proposal

## Why

ETHOS adopts, upgrades and hands off a repository, but it offers no native exit:

- `ethos hook install` replaces the repository's Git-common `core.hooksPath` and ref-storage
  configuration without recording what it replaced
  (`src/ethos/adapters/repo/hook/activation.py`).
- A repository that still selects an installation through `ethos/runtime/CURRENT` and `ROLLBACK`
  keeps it alive for `retire-supply`.
- The release journey's uninstall step removes only the console, and its
  `live_consumer_safe_uninstall` is `not_qualified`.

On 2026-11-04 two archived introduction films were unbound by hand, so that four old
installations, about 2.7 GB, could retire. The design review that evening, adopted at 22:21 with
the conditions that [design.md](design.md) carries, settles the shape:

- install records the preimage it replaces;
- a public exit command restores only values that ETHOS owns, or the recorded preimage;
- nothing is guessed.

## What Changes

This Change delivers the first slice:

- From this release on, `hook install` records the hooks-related configuration it replaces. The
  record covers both scopes, and an absent value is recorded as absent. Install writes it only on
  first adoption, or when it replaces a value that ETHOS does not own. Upgrades and re-installs
  never overwrite it, and it is written inside the activation transaction, so a failed activation
  leaves none.
- `ethos adopt --exit --json` previews the exit without any effect. The preview reports:
  - the Git-common configuration and what the exit would restore it to;
  - the CURRENT and ROLLBACK selector bytes with their hashes, and the installations they name;
  - each linked worktree's own hooks path;
  - what blocks the exit: a valid or unknown Lease, the held selection lock, or a held proof slot;
  - the Lease snapshot, and a plan digest over all of these.
- Without a recorded preimage, the preview requires the user's choice, because unsetting the hooks
  path would itself be a guess.
- The exit's apply, which restores the configuration and removes the selectors under the fenced
  order of the review, follows as the next slice. Until then, `--exit --apply` refuses with
  `adoption_exit_apply_unavailable`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: installation records the configuration it replaces, and a repository exit
  is previewed before any effect.

## Impact

- `src/ethos/adapters/repo/hook/`: `preimage.py` (new), `exit.py` (new) and `activation.py`.
- `src/ethos/domain/adoption.py` and `src/ethos/surface/cli/root/adoption.py`.
- The command reference and the hook tests.
