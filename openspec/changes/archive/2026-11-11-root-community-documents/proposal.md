# Proposal

## Why

GitHub reads a project's community health files by fixed names at the root of a repository, in
`.github/` or in `docs/`. The repository paradigm admits only `AGENTS.md`, `CHANGELOG.md`,
`CONTRIBUTING.md`, `LICENSE`, `NOTICE`, `README.md` and `VERSION` as root entry documents, so
`ethos lane prewrite` refuses a governed repository's root `SECURITY.md` or `CODE_OF_CONDUCT.md`.
The owner asked for the industry practice, which GitHub's documentation defines.

## What Changes

- The root catalog's entry documents admit the Markdown community health files that GitHub's
  documentation names beside `CONTRIBUTING.md`: `ACCESSIBILITY.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md` and `SUPPORT.md`. As entry documents they are also fixed names.
- The 0.2.0-beta.8 entry gains an Added line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement "The root carries only protocol entries" defers its list of entry documents
to the packaged paradigm catalog; only that catalog's data changes, so `skip_specs: true` applies.

## Impact

`src/ethos/contracts/paradigm/paradigm.toml`, `tests/unit/repository/test_paradigm_report.py` and
`CHANGELOG.md`.
