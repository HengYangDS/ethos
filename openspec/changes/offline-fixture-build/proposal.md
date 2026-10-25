# Proposal

## Why

Offline proofs build the tracked `quality-sample` fixture project with `uv run --locked --offline`. Its build backend requirement, `hatchling>=1.32.4`, is not locked, so an offline build resolves it against uv's cached package index. Every uv command on the host shares that cache. Suppose any command refreshes the index after a dependency of the backend publishes a release. Offline resolution then selects that release, whose wheel is not cached, and the proof fails. On 2026-10-25 an alpha.14 proof failed this way on tomlkit 0.15.2. Warming the cache cannot prevent it, because a later refresh can always list a newer release.

## What Changes

- The `quality-sample` fixture builds with uv's bundled build backend, `uv_build`. Its requirement admits every supported uv, so a fixture build needs no download and no cached build requirement.
- A regression proves that every tracked fixture project builds offline from an empty uv cache.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: offline fixture builds need no unlocked build supply.

## Impact

The change touches `tests/fixtures/quality-sample/pyproject.toml` and `tests/unit/ci/test_ci_bootstrap.py`. The fixture's dependencies, its lock and the tests that use it stay as they are. Out of scope: how ETHOS builds itself, and how the Python quality gate treats adopters' build backends.
