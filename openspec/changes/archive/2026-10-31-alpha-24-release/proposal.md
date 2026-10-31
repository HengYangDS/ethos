# Proposal

## Why

`v0.2.0-alpha.23` fails on GitLab Windows ARM64 jobs: the interpreter path inside its release
archive pushes a deep job directory past the Windows path limit ("exit status 6"). The
`adopter-reported-repairs` Change fixed that, refused compensation of a published archive, and let
the code ceiling receive verified byte-bound carriers. Adopters install only published releases.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.24`. No lock, supply or test
  changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.24` entry. It describes every user-visible
  product change since `v0.2.0-alpha.23` and the known advisories in the release's shipped bytes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json` and `CHANGELOG.md`. No lock, supply image or product
code changes: none of the eight inputs that the supply image hashes changed since `v0.2.0-alpha.23`.
