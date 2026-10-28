# Proposal

## Why

The prepared `0.2.0-alpha.18` entry (Change `alpha-18-release`, landed at `a6ad56b67`) was never
tagged. Hosted Windows host conformance failed with `hook_runtime_manifest_invalid` on its head,
and the fix landed after it. A tag carries everything its entry lists, so the entry must name what
landed since and what the shipped bytes are now known to carry:

- host-store retention no longer removes an installation that a repository is about to select, and
  it creates nothing in a repository without ETHOS state;
- the wheels and installed runtimes ship uv 0.13.5 as a production dependency. Its embedded rustls
  0.23.45 carries four advisories, published on 2026-10-27, that no uv release fixes yet.

## What Changes

- The `[Unreleased]` Fixed note moves into the `0.2.0-alpha.18` entry.
- The entry gains a Security section for uv's embedded rustls, as the `0.2.0-alpha.16` entry did
  for npm's bundled packages.
- The entry is dated with the tag date, 2026-10-29.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`CHANGELOG.md` changes. Product behavior does not change.
