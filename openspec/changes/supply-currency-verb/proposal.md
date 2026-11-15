# Proposal

## Why

Keeping pinned supply current is a repeated operation without a product verb. The adoption
session measured it on 2026-11-15 with a private tool set of 358 lines, written after a security
release of one runtime sat unmoved for three days:

- At a release age of 0 hours, 10 of the 12 governed repositories that are not frozen were behind
  on at least one pinned source: an exact package pin, a tool that the toolchain locks, or a lock
  that could move.
- One repository was current and one is frozen.
- Each owner schedules the move by hand after a message.

Each repository declares its own release age, and nothing reads that declaration against its
pins.

## What Changes

- One read-only projection for a repository lists each declared supply source with its pinned
  release and the newest release that the repository's declared age admits, and flags a security
  release.
- It adds no second declaration and arms nothing: it is a report.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

A reader over the lockfiles and the toolchain declaration. It follows the fleet projection in
the order after the stable release.

Owner: the release lead. Next action: place it in the order after 0.2.0. Read again: after 0.2.0.
