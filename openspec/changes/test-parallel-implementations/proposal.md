# Proposal

## Why

The parallel-implementation gate covers `src/` and `tools/` only. Measured at `c89ac1884` with the
gate's own equivalence, `tests/` holds 30 groups of identical function bodies: fixtures, readers,
fake clocks and helpers copied from module to module. Scanning tests together with product code
finds two more groups: a test copy of a product digest and a tools copy of a test helper. A fix
reaches one copy only, so each copy is a parallel implementation.

## What Changes

- The gate measures `src/`, `tools/` and `tests/`. A `test_` function's decorators join its shape,
  so two tests that share a body but differ in parameters are not copies.
- 28 groups get one owner each: a fixture in the `conftest.py` of the nearest common directory, a
  helper in `tests/support`, or an existing owner such as `subprocesses.completed` and
  `unittest.mock.Mock(side_effect=...)`. Groups 15 and 29 are parametrized tests, not copies.
- The journey test states its expected digests as data instead of copying the product's digest.
- `ethos.adapters.repo.runtime.filesystem.runtime_executable` becomes the one owner of a virtual
  environment's executable path, used by `tools/ci/delivery/acceptance/effect.py` and the test
  support.
- In the source budget's enforced line-equivalents at `c89ac1884`, `python_tests` falls by 139
  (99,933 to 99,794), product grows by 6 and tools fall by 5.
- `custody_path`, the store's own layout, becomes public, and the test support's copy of that
  layout goes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. ETHOS's own quality gate and tests change; no requirement changes.

## Impact

67 files: 65 under `tests/` (new `conftest.py` files in `tests/architecture`, `tests/unit`,
`tests/unit/adapters/gates`, `tests/unit/adapters/repo/hook` and
`tests/unit/adapters/store/retention`; new `tests/support/clock.py`), plus
`src/ethos/adapters/repo/runtime/filesystem.py` and `tools/ci/delivery/acceptance/effect.py`.
