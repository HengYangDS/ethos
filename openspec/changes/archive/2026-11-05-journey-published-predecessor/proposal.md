# Proposal

## Why

beta.2's release run 41976538980 published all five runtimes and the GitHub release on
2026-11-05. Both journey legs then failed within 12 seconds, with
`release_journey_download_failed:v0.2.0-beta.1:release not found`.

The journey takes its upgrade predecessor from the changelog entry that follows the prerelease
(`tools/ci/delivery/acceptance/journey.py`, `previous_version`). The distribution specification
states that rule. On 2026-11-05 the owner decided not to publish 0.2.0-beta.1: its tag exists, but
it has no GitHub release, and its changelog entry records that. So the next changelog entry is not
always the previous published release. The forge, not the changelog, says what was published.

## What Changes

- The journey walks the changelog entries after the prerelease, in order, and takes the first one
  whose GitHub release exists as its upgrade predecessor.
- The receipt names every version it skipped as `skipped_unpublished`, so the evidence shows which
  predecessor was used and why.
- With no published predecessor, the journey refuses with `release_journey_previous_missing:<v>`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the journey's previous release is the latest earlier release that the forge
  published, not merely the next changelog entry.

## Impact

`tools/ci/delivery/acceptance/journey.py`, its tests, the distribution specification and the
changelog.
