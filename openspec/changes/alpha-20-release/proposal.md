# Proposal

## Why

`v0.2.0-alpha.19` refuses governed repositories' patches for references they own or never make, so
adopters cannot land prepared migrations: di-effect's Gitleaks and Taplo migrations stop at
`import:yaml` and `executable:app`. The accepted `dev` carries the repair, Change
`reference-owner-semantics`, and adopters install only published releases.

## What Changes

- `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version
  tests move to `0.2.0-alpha.20`.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.20` entry. It describes every user-visible
  product change since `v0.2.0-alpha.19` and the known advisories in the release's shipped bytes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `package-lock.json`, `CHANGELOG.md` and three version
tests change. Product behavior does not change.
