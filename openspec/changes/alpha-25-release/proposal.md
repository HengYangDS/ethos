# Proposal

## Why

`v0.2.0-alpha.24` blocks every proof on a Windows host whose code page is not UTF-8: the GitLab
Windows ARM64 jobs of data-department-work-guidelines stop with "'gbk' codec can't decode byte 0x94"
(pipeline 13536, job 62963). The `locale-independent-text` Change makes ETHOS read and write process
and file text as UTF-8 whatever the host locale, and runs every Python process ETHOS starts in UTF-8
mode. Adopters install only published releases.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.25`. No lock, supply or test
  changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.25` entry. It describes every user-visible
  product change since `v0.2.0-alpha.24` and the known advisories in the release's shipped bytes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json` and `CHANGELOG.md`. No lock or supply image change: none
of the eight inputs that the supply image hashes changed since `v0.2.0-alpha.24`.
