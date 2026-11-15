# Proposal

## Why

The product design contract promises one public reconciler for Work Lanes. Today a lane's
lifecycle is a set of commands, thirteen by the count of the committee of 2026-11-14, and a named
surface batch after 0.2.0 merges them into that reconciler. Their names will change then.

The committee recommended, and the owner decided on 2026-11-15, that 0.2.0 makes no compatibility
promise for those command names and that the release entry says so. DR-0029 records the
committee's changes to the gate and does not state this sentence; this draft keeps it until the
entry is written.

## What Changes

- The release entry of the batch that publishes the public normal path names the lifecycle
  commands, listed from the catalog, and states that their names carry no compatibility promise in
  0.2.0 and that a result's next step is the supported way to continue.
- The command reference marks the same commands.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md` and the command reference. No behavior changes.

Owner: the release lead. Next action: list the commands from the catalog and write the sentence
with the surface texts. Read again: at the cut of 0.2.0-beta.14.
