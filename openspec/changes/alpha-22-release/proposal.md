# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.21` lacks three product changes that
the accepted `dev` carries:

- `per-file-ceiling-parameters`: both per-file ceilings default to 500, and a governed repository
  may declare its own whole-tree value in `.ethos/rules.toml` `[paradigm.size]`. The owner set 500
  for ETHOS and every governed repository on 2026-10-31.
- `deleted-input-dependency`: deletion admission admits a patch that replaces a vendored Python
  package with a declared dependency of the same name. An adopter lane cannot retire its vendored
  copy of `filmkit` without it.
- `hosted-flake-repairs`: on Windows, publishing a just-qualified native tool outlasts the hold that
  Windows keeps on its image instead of failing with `WinError 32`.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.22`. No lock or test changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.22` entry. It describes every user-visible
  product change since `v0.2.0-alpha.21` and the known advisories in the release's shipped bytes.
- The GitLab supply image stays bound. None of its eight inputs has changed since it was built from
  `c36790cd8`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json` and `CHANGELOG.md` change. Product behavior does not
change.
