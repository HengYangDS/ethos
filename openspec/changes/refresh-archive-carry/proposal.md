# Proposal

## Why

Archive provenance follows refresh edges from an archive commit that a lane refresh rewrote, so a
rebased lane still finds its archived Change. It also keeps following edges from a commit that is
already in current history. A fast-forward refresh moves a branch past such a commit without
rewriting it, so that edge carries the archive onto the refresh target.

On 2026-11-07 the agent-native lane was refreshed from `bfaa87543`, the archive of
`provider-timeout-report`, to dev `e542a8909`, the archive of `bounded-result-readers`. Both
archives then resolved to `e542a8909` at distance 0. Every root at that head refused with
`openspec_archive_attestation_ambiguous`: `ethos status` in both lanes, and `lane prewrite` for a
new Change.

## What Changes

- A commit that is already in current history is the preserved archive. Resolution takes its
  ancestry distance and follows no further refresh or repair edge from it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `src/ethos/adapters/openspec/lifecycle/archive_provenance.py` and
  `tests/unit/adapters/openspec/test_archive_provenance.py`.
