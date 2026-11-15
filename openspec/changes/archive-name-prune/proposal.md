# Proposal

## Why

Tracked text names a governed repository only by its shape and count. A read-only measurement of
2026-11-13 found 17 archived Changes, 96 files, that name one governed repository family, and two
decision records that name governed families in one sentence each. No tracked file outside the
archive cites the paths of those Changes.

The owner decided on 2026-11-15 that they leave the newest tree in 0.2.0-beta.13 and that history
stays as it is.

## What Changes

- The 17 archived Change directories leave the current tree, as `repository-governance` allows for
  pruned archived Changes. Git ancestry and the release tags keep every removed file.
- The two decision records describe the families by shape. No decision, date or status changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies.

## Impact

`openspec/changes/archive/` and two decision records. No product code, test or specification
changes. The list of directories is local evidence of the releasing session and is not tracked. A
tracked owner for the naming rule and a check that enforces it are a separate Change.

Owner: the release lead. Next action: open its tasks at the cut of 0.2.0-beta.13 as that batch's
one off-gate row. Read again: 2026-11-26.
