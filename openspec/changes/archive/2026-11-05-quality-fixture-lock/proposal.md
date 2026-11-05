# Proposal

## Why

The integrated beta-3 proof `ib2` at `e979102f9` failed 8 tests in
`tests/unit/adoption/quality/native/test_nox.py`, each with
`quality_behavior_python_native_dependency_floor_unbound`. The native behavior gate checks that the
session's environment satisfies the fixture's lock with `uv sync --check --frozen`. The fixture's
sessions run in the repository's own environment, so the fixture lock must pin the same versions as
the repository lock for every package they share.

The Python lock move in `python-supply-day-old` raised coverage from 7.17.0 to 7.17.1 in `uv.lock`
but not in `tests/fixtures/quality-sample/uv.lock`. Earlier moves updated both, as `0b1c1b928` did.
Nothing states the rule, so the drift surfaced only as a downstream evidence failure.

## What Changes

- The quality fixture locks coverage 7.17.1, the repository's version.
- A test states the rule: every package that both locks pin has the same version in each, and a
  difference names the package and both versions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This keeps a test fixture consistent and adds a test, so `skip_specs: true` applies.

## Impact

`tests/fixtures/quality-sample/uv.lock` and a new `tests/architecture/test_quality_fixture_lock.py`.
