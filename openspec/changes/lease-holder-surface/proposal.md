# Proposal

## Why

A Work Lane's holder cannot read or renew its own Lease through one native step.

- `ethos lane lease renew` and `resume` require `--generation`, `--expires-at`, `--branch` and
  `--holder-ref`. Without them the command fails with a usage error, and no preview reads them.
- `ethos status --json` for a holder is about 34 KB, over its 16 KiB payload budget, so ETHOS moves
  all of `data` into an artifact file. The inline `summary` keeps the branch, role and counts, but
  not the Lease, so the holder must open the artifact to read its own expiry.

Lacking both, the agent kits read ETHOS's private `.git/ethos/state.sqlite`: 16 of 931 kit scripts
counted on 2026-11-05. The owner asked whether the command line had been designed at all.

## What Changes

- `ethos status` names the current Work Lane's Lease in its inline summary: generation, expiry and
  seconds left. The summary survives the payload budget. With less than two hours left, the next
  action is the renewal preview.
- `ethos lane lease renew` and `ethos lane lease resume` without Lease coordinates preview from the
  current Work Lane's Lease and return the exact apply command. An apply still binds all four
  coordinates, so the compare-and-swap is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: the holder reads and renews its Lease through native commands.

## Impact

`src/ethos/surface/cli/lane/lease.py`, the status summary in `src/ethos/domain/inspection.py`, their
tests and the command reference. The `.git/ethos` store layout is unchanged and stays private.
