# Proposal

## Why

`gate-fail-closed` changed what every governed repository sees in a proof: one gate's failure is
now that gate's own outcome rather than a crashed or emptied proof. It landed without a
`CHANGELOG.md` entry, so the beta.7 release notes would omit a change that adopters' owners read
to understand their proofs.

## What Changes

- `CHANGELOG.md` `[Unreleased]` `### Changed` gains one bullet for the contained gate failure,
  naming its gaps and verdict classes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The behaviour and its requirement landed with `gate-fail-closed`; this Change records it.

## Impact

- `CHANGELOG.md` only.
