# Proposal

## Why

beta.8 is a fix release. An adopter's first redaction under beta.7 refused a forge web address on
its own port, because the protected-peer feed did not read the host and port of `forgeRepository`;
that adopter's redaction and its own first release wait for a released runtime with the fix. The
release also carries the test fixture authority and the test budget step that landed after beta.7.

## What Changes

- `VERSION` moves to `0.2.0-beta.8`.
- The `[Unreleased]` entry becomes the `0.2.0-beta.8` entry, completed from the landed Changes and
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
