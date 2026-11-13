# Proposal

## Why

beta.10 is the weekly batch under D19, a week after beta.6's batch of 2026-11-07. Since beta.9 it
carries the layout rules for Markdown lists, canonical text and package markers, with the staged
check that `pre-commit` runs and its fix under an installed runtime; the product budget step to
85,000; the repair preview as the paradigm's next action; README files as bounded directory
indexes; one NUL-terminated reader of `git worktree list`; and the supply move with Node.js 26.13.1,
a security release.

## What Changes

- `VERSION` moves to `0.2.0-beta.10`.
- The `[Unreleased]` entry becomes the `0.2.0-beta.10` entry, completed from the landed Changes and
  the release build's audit. It names the upgrade paths its journey qualifies, the journeys this
  beta does not qualify, every advisory the audit reports, and the known open defects a user can
  meet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md` and `VERSION`.
