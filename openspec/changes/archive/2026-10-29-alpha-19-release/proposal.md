# Proposal

## Why

`v0.2.0-alpha.18` lacks the changes accepted after it:

- Git hooks start the ETHOS runtime only for a reference transaction's prepared state;
- ETHOS judges its own tree by the obligations it ships for every repository, and the shared Python
  static floor follows the import-sorting values that a repository declares;
- a focused check that verifies no code compiles no code obligation, and a provider failure
  reported from a nested command scope no longer stops its sibling gates;
- the product npm lock replaces re2js 2.8.6, whose lookbehind matching takes quadratic time
  (GHSA-gg6h-894w-4m9c, high), with 2.8.8.

Adopters install only published releases, and the `v0.2.0-alpha.18` runtime runs re2js 2.8.6 in the
Node supply of every adopter's markdown lint gate.

## What Changes

- `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version
  tests move to `0.2.0-alpha.19`.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.19` entry that describes every user-visible
  product change since `v0.2.0-alpha.18`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `package-lock.json`, `CHANGELOG.md` and three version
tests change. Product behavior does not change.
