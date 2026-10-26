# Proposal

## Why

`v0.2.0-alpha.15` lacks the fixes accepted since 2026-10-26. These are:

- a refused commit to a protected branch keeps its content;
- retained adopters migrate their owned legacy Work Lane names;
- explicit runtime supply is validated against its own manifest;
- runtime materialization accepts uv interpreters listed by a relative path;
- a Darwin cleanup race no longer replaces a command's own failure;
- status and prewrite verify only the signature repairs that affect an archive commit;
- the commit hook judges both sides of a staged rename;
- lane retirement on macOS ignores FIFOs that `lsof` reports by inode alone.

Adopters rebind once, to one release that carries all of them.

## What Changes

- `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version
  tests move to `0.2.0-alpha.16`.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.16` entry that describes every
  user-visible product change since `v0.2.0-alpha.15`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `package-lock.json`, `CHANGELOG.md` and three version
tests change. Product behavior does not change.
