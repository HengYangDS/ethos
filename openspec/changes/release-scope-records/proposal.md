# Proposal

## Why

Two release decisions of the 0.2.0 plan exist only in conversation and in ignored drafts. On
2026-11-07 the owner narrowed the 0.2.0 release scope that DR-0015 declared: Windows x64 is not
declared, Linux arm64 is, Homebrew is conditional and the GitLab CI component is not qualified. The
release candidate gate of the expert committee's resolution and the weekly D19 cadence also bind
0.2.0. On 2026-11-05 the owner decided that 0.3.0 separates immutable build identities from
evidence-gated `beta`, `rc` and `stable` channel pointers. The `rc-plan` design (family 1) names both
records as its first Changes. It planned the channels record as DR-0020, but that number went to the
product budget step, so the channels record is DR-0022.

## What Changes

- DR-0021 records the 0.2.0 release scope and supersedes DR-0015's host list, keeping the rest of
  DR-0015 in force.
- DR-0022 records the 0.3.0 release channels decision and leaves the identity scheme and the channel
  carrier to the Change that implements it.
- The decisions README indexes both and notes on DR-0015 that its 0.2.0 host list is superseded.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The records carry rationale; the distribution specification does not list hosts, so
`skip_specs: true` applies.

## Impact

- `docs/decisions/dr-0021-release-scope-0-2-0.md`, `docs/decisions/dr-0022-release-channels-0-3-0.md`
  and `docs/decisions/README.md`.
- The release Changes of the `rc-plan` families 7 and 8 cite DR-0021 for the declared journeys.
