# Proposal

## Why

The owner asked for every supply chain to move to its newest stable release, and on 2026-11-13 set
the default release age to zero: a release is eligible when it is published, and a repository may
declare a longer age for itself. ETHOS last moved its supply in `supply-move-1113`, which held Mise
at 2026.10.25 with the python-build-standalone 20261110 build of CPython 3.14.10, and Prettier at
3.9.10 until its layout change was scanned across the governed repositories. Both holds are
released: the cause of the Mise refusal is known, and the scan found one changed file in ETHOS and
none in the three adopters it read.

## What Changes

- Mise moves from 2026.10.25 to 2026.11.8: the configuration's floor, the CI bootstrap version and
  its six executable digests. Its lock takes uv 0.13.8, Vale 3.27.0 and the python-build-standalone
  20261110 archives of CPython 3.14.10.
- The npm pins move to Prettier 3.10.1, markdownlint-cli2 0.24.1 and ESLint 10.15.0, the `glob` and
  `minimatch` overrides to 14.0.6 and 11.0.8, and the lock's transitive packages follow.
- The Python lock moves `coverage` 7.17.3, `cyclopts` 5.5.0, `fastmcp` and `fastmcp-slim` 4.2.0,
  `grimp` 3.20, `humanize` 4.17.0, `pydantic-settings` 2.16.3, `ruff` 0.17.5, `ty` 0.0.104 and
  `uv` 0.13.8, and the floor of each moved direct dependency rises to its locked version.
- Prettier 3.10.1 reformats one tracked file, the JavaScript test reporter.
- The CI supply image's base moves to the uv 0.13.8 image that matches the uv pin; the image is
  rebuilt from the moved locks and bound by digest.
- The Unreleased entry names the moves.

Already newest, and unchanged: Node.js, CPython's version, CUE, Go, actionlint, scc, Gitleaks, Syft,
Grype, the OpenSpec CLI, the other npm pins and the six action pins. `complexipy` stays at 8.3.0:
version 9.0.0 scores cognitive complexity differently, so 79 functions exceed their allowance and
273 pins go stale under the baseline that the decision-density test pins to the 8.x scores; pinning
the baseline again is its own Change. Python 3.15 stays outside `requires-python`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Locked versions change; no requirement changes.

## Impact

`.config/mise/config.toml`, `.config/mise/mise.lock`, `.config/checks/ci-projection/policy.toml`,
`package.json`, `package-lock.json`, `pyproject.toml`, `uv.lock`,
`tests/fixtures/quality-sample/uv.lock`, `src/ethos/adapters/gates/javascript/reporter.mjs`,
`.config/ci/supply/Dockerfile`, `.config/ci/pipeline.cue` with its generated projections, and
`CHANGELOG.md`.
