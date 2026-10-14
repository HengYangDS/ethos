## Why

Two defects in the proof loop each cost a full proof cycle on 2026-10-13.

- `test_command_scope_conserves_one_deadline_across_native_calls` depends on wall-clock headroom: a 0.6 s child must finish inside a 1.0 s scope, so interpreter start-up under host load fails it. Three repository proofs failed this way at load 100 or more, and the earlier fix (6cdf55a5b) only widened the margins.
- When the archive merge leaves a canonical spec that strict validation rejects, `ethos lane archive-change` blocks with a bare `openspec_validation_failed:spec:<capability>`. The native issue that explains it, such as a requirement body over 500 characters, is dropped, so the cause has to be rediscovered by simulating the archive.

## What Changes

- The deadline-conservation test drives the adapter's own clock. It asserts that a nested command receives exactly the caller's remaining budget, so host load can no longer decide the outcome.
- A blocked archive carries every blocking native validation issue of the rejected items (item, severity, path, message) as diagnostics. Gaps, repair continuation and compensation stay unchanged.

## Impact

- Tests: `tests/unit/adapters/test_process.py`, `tests/unit/lanes/lifecycle/archive/test_effect_boundaries.py`.
- Code: `src/ethos/adapters/openspec/lifecycle/validation.py`, `src/ethos/adapters/mutation/lane_lifecycle/archive/effect.py`, `src/ethos/surface/cli/lane/lifecycle.py`.
- Specs: command-plane gains one requirement for archive validation diagnostics.
