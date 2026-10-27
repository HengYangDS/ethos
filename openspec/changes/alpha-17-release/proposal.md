# Proposal

## Why

`v0.2.0-alpha.16` lacks the changes accepted after it:

- runtime generation reclamation no longer defers when another process deletes a path that a
  running command names while reclamation observes it, so a full proof no longer fails while
  removing nothing;
- the decisions index lists every decision number, and the product design contract, the Docs
  Registry and the glossary that the wheel ships are current.

Adopters rebind once, to one release that carries both.

## What Changes

- `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version
  tests move to `0.2.0-alpha.17`.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.17` entry that describes every
  user-visible product change since `v0.2.0-alpha.16`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `package-lock.json`, `CHANGELOG.md` and three version
tests change. Product behavior does not change.
