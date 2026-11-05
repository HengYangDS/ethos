# Proposal

## Why

The signed tag `v0.2.0-beta.1` (`c99547a99`, commit `ea72a93bb`) is on both peers, but its release
run never published assets:

- The first attempt, 41892426370, refused publication with
  `release_assets_platform_missing:macos-arm64`, because GitHub cancelled the macOS runtime build
  without a runner.
- The rerun on 2026-11-05 failed the macOS build's dependency audit. npm 12.2.2, published
  2026-11-04 23:02 UTC, fixes six of the eight advisories that beta.1's npm 12.2.1 carries. Under
  the dependency acceptance policy, all eight therefore block.

On 2026-11-05 the owner decided not to publish beta.1, so no release ships known-fixable
vulnerabilities. Adopters move from 0.2.0-alpha.30 straight to 0.2.0-beta.2, which ships npm
12.2.2. A published tag is never rewritten, so the tag stays as history.

## What Changes

- The `0.2.0-beta.1` entry gains one line: the version was tagged but never published, and
  0.2.0-beta.2 supersedes it.
- The `0.2.0-beta.2` entry says it is the first published beta, upgrading from 0.2.0-alpha.30.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release-notes correction changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`.
