# Proposal

## Why

The 2026-11-07 expert committee's channel resolution, which the owner accepted on 2026-11-07,
lists npm among the channels ETHOS never ships, and R8(f) retires the npm launcher before the stable
release path. `distributions/npm` still carries a Node launcher that runs the Python command plane
through `uv`, a second version carrier that every release must move, a JavaScript test and launcher
requirements in the distribution specification. Nothing installs ETHOS through it: the release
ships per-platform archives through Mise, and the release Change's version step names the launcher
manifest only because it exists.

## What Changes

- **BREAKING** for anyone running `npm run ethos`: `distributions/npm`, its launcher test and the
  root `ethos` and `test:npm` scripts are removed. Node stays for the JavaScript tools that the
  locked `package.json` declares.
- The release version has one carrier, `VERSION`; the release identity keeps refusing a version in
  the root `package.json` or `package-lock.json`.
- The product boundary, format selection and JavaScript coverage stop naming the launcher.
- The distribution specification drops the launcher requirements and states the Node runtime
  policy for the JavaScript tools.
- The README, the release guide and the distribution explanation stop describing the launcher.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: no npm launcher; Node serves only the repository's JavaScript tools.

## Impact

- `distributions/npm/`, `package.json`, `tests/architecture/npm-package.test.mjs`,
  `tools/ci/sessions.py`.
- `src/ethos/repository/release/identity.py`, `src/ethos/repository/release/configuration.py`,
  `src/ethos/repository/policy/boundary/`, `.config/checks/format-selection/policy.toml` and their
  tests.
- `README.md`, `docs/guides/release-and-publication.md`, `docs/architecture/distribution.md`,
  `CHANGELOG.md`.
