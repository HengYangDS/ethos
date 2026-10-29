# Proposal

## Why

The prepared `0.2.0-alpha.19` entry (Change `alpha-19-release`, landed at `0ba9a7e44`) names the
advisories in uv's embedded rustls but not those in the npm that the wheels and installed runtimes
ship. Before the tag, the release build's own audit on `0ba9a7e44` reported six advisories in the
packages that npm 12.2.1 bundles, and no npm release fixes them yet:

- undici 6.29.0: GHSA-4qv8-2p9j-2685 (medium) and GHSA-xjj6-f33q-929c (high), which the
  `0.2.0-alpha.16` entry lists, and GHSA-2m5v-pch6-74hx and GHSA-qrxm-fqhp-jwvm (high) and
  GHSA-9fm3-97px-rjf6 (medium), published on 2026-10-27, which no entry lists;
- ip-address 10.7.2: GHSA-rxp7-6hxx-x8q5 (medium), which the `0.2.0-alpha.16` entry lists.

`v0.2.0-alpha.17` and `v0.2.0-alpha.18` ship the same npm. A tag's entry names the known advisories
in its shipped bytes.

## What Changes

- The `0.2.0-alpha.19` entry's Security section gains a note for npm's bundled undici and
  ip-address, as the `0.2.0-alpha.16` entry did when it first shipped them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`CHANGELOG.md` changes. Product behavior does not change.
