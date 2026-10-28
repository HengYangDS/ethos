# Proposal

## Why

On 2026-10-28, both full proofs of `stable-check-names` failed for one reason only: pytest-timeout stopped a test at the 120 s per-test bound. The first proof stopped `test_public_maintenance_release_preserves_shared_trains[accepted_ff]`, the second `test_source_and_release_builds_preserve_exact_metadata`. Earlier that day, `surface-pruning` lost a proof the same way. No test hung. Run alone, the eight heaviest tests take 32–51 s. Inside a full proof, they run 94–126 s, because the longest-first order starts them together on 12 workers next to `local-install-smoke` and `build`.

The 120 s value is meant as a hang guard, but it was sized for an uncontended run. It therefore fails healthy tests whenever the host is busy within the admitted load. Three journeys already declare their own 240 s budget to escape it (`d378539a3`, `c2871528e`, `eafefd60c`), and each new heavy test would need another.

## What Changes

- **One hang bound.** `.config/checks/pytest/pytest.toml` declares 600 s. That is about 12 times the slowest test run alone and about 5 times the slowest full-proof observation. A test that stops making progress still fails at that bound and reports its stack.
- **No upward exceptions.** The three `@pytest.mark.timeout(240)` budgets are removed. The deliberately short bounds of 2, 5 and 30 s stay, because each one times a specific fast operation.
- **Regression.** A test-level timeout may only tighten the declared bound.
- **Specs.** quality adds the requirement that the per-test bound detects hangs, not slowness.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: the per-test bound detects hangs, not slowness.

## Impact

- No product Python changes.
- A hung test now holds its worker for up to 10 minutes before it fails, instead of 2 minutes (4 for the three journeys). `--maxfail=1` still ends the run at that first failure.
- What the tests cost is unchanged. Reducing the subprocess volume of the heavy tests, and declaring the 12 workers in the gate's `cpu_reservation`, are separate throughput work.
