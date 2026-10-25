# Proposal

## Why

Two assumptions about the host that runs ETHOS's tests broke its proofs on 2026-10-25.

- **Offline fixture builds.** Offline proofs build the tracked `quality-sample` fixture project with `uv run --locked --offline`. Its build backend requirement, `hatchling>=1.32.4`, is not locked, so an offline build resolves it against uv's cached package index. Every uv command on the host shares that cache. When any command refreshes the index after a dependency of the backend publishes a release, offline resolution selects that release, whose wheel is not cached, and the proof fails. An alpha.14 proof failed this way on tomlkit 0.15.2. Warming the cache cannot prevent it, because a later refresh can always list a newer release.
- **CI detection.** Native mise trusts every configuration while a CI marker is set, whatever its value. The markers are `CI`, `GITHUB_ACTIONS` and `GITLAB_CI`, among others. Three regressions that need an untrusted configuration assumed a host without those markers. On GitHub, the first hosted verification of 0.2.0-alpha.14 failed on one of them, so its tag waits for this fix.

## What Changes

- The `quality-sample` fixture builds with uv's bundled build backend, `uv_build`. Its requirement admits every supported uv, so a fixture build needs no download and no cached build requirement.
- A regression proves that every tracked fixture project builds offline from an empty uv cache.
- The trust regressions that need an untrusted configuration first hide the CI markers of the hosts that run them. They then require native mise to report the root untrusted, so an unknown CI marker fails with a precise message instead of a false result.
- The 0.2.0-alpha.14 entry is dated 2026-10-26, the day its tag is created.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: offline fixture builds need no unlocked build supply.

## Impact

Tests: `tests/fixtures/quality-sample/pyproject.toml`, `tests/unit/ci/test_ci_bootstrap.py`, the new `tests/support/mise_host.py`, and the three trust regressions in `tests/unit/adapters/toolchain/test_mise_boundary.py`, `tests/unit/ci/test_native_tool_cache.py` and `tests/unit/adoption/quality/test_evidence.py`. The changelog dates the 0.2.0-alpha.14 entry.

Product behavior does not change. Resolution keeps asking native mise, and native mise's own CI policy keeps counting as one of the caller's trust inputs. The fixture's dependencies, its lock, and the tests that use it stay as they are.

Out of scope: how ETHOS builds itself, and how the Python quality gate treats adopters' build backends.
