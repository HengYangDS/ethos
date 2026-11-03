# Proposal

## Why

The shipped adopter CI model, `.config/ci/verification.cue`, pins `jdx/mise-action` 5.2.5
(`6612f0ef`). Release 5.2.6 (`f5be966e`, published 2026-11-02 and marked latest) fixes a step that
hung when a cache restore failed mid-download. Adopters' generated workflows take the action from
this model, so they move only when it moves, and ETHOS's supply rule selects the latest stable
release.

## What Changes

- Pin `jdx/mise-action` 5.2.6 by its commit in the shipped adopter CI model.
- Record the move in `CHANGELOG.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This moves a supply pin, so `skip_specs: true` applies.

## Impact

`.config/ci/verification.cue` and `CHANGELOG.md`. ETHOS's own workflows do not use the action, so
its projections do not change; adopters receive the pin with the next release.
