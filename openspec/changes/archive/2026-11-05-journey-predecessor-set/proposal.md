# Proposal

## Why

The hosted journey that qualified 0.2.0-beta.2 upgraded only from 0.2.0-alpha.30, the latest
earlier published release. On 2026-11-05, 8 of the 12 governed repositories still selected
0.2.0-alpha.29 and will upgrade from it directly. That upgrade and its rollback were never
exercised: DDWG and wib went through alpha.30, which proves the two hops but not the direct one.
Codex 019f4fbf named the gap while reviewing beta.2 for di-effect and alphasim, and holds their
binding until the direct path is verified.

The cause is in the qualification itself. The beta criterion names an upgrade "from the previous
release", and the journey has no way to upgrade from anything else. So a release that adopters
reach from older releases is qualified only on the path that the fewest of them take.

## What Changes

- A beta's journey evidence covers the upgrade, with its rollback, from the previous release and
  from every earlier published release that a governed adopter still selects.
- The journey accepts named predecessors. A `journey_previous` dispatch input carries
  comma-separated published prerelease tags. Each one must be an earlier changelog entry whose
  release the forge published. The journey upgrades from each in its own host store and rolls
  back to it. Without the input, the predecessor stays the latest earlier published release.
- The cold install, host-store pinning, hook binding, full proof and uninstall still run once
  per leg. Only the upgrade and its rollback repeat per predecessor.
- The receipt names every predecessor, records each predecessor's verified assets, and keys
  `upgrade_and_rollback` by predecessor tag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the beta criterion, the hosted journey and the journey's predecessor selection.

## Impact

`tools/ci/delivery/acceptance/journey.py`, the `release_journey` session in `tools/ci/sessions.py`,
the `ETHOS CI` dispatch inputs in `.config/ci/pipeline.cue` and its GitHub projection, the release
guide, and the journey's unit and architecture tests. The receipt's `previous` becomes a list, and
`upgrade_and_rollback` becomes a mapping keyed by predecessor tag.
