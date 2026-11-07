# Proposal

## Why

macOS's `com.apple.bsd.dirhelper` runs daily at 03:35. It removes files under the per-user
temporary directory that were not accessed for three days. The behavior probe builds its locked
test environment under `$TMPDIR`. uv installs that environment from its cache, so the files keep
the cache's old access times, and the probe reads bytecode from its cache prefix rather than the
sources. A proof that runs over 03:35 therefore loses venv sources during the run and fails with an
import error. This happened on 2026-11-05 at 03:36 and on 2026-11-07 at about 03:35 (register row 9).

The gitleaks mirror copies tracked files into `$TMPDIR` with `copy2`, which keeps the source's old
times. A file the cleaner removes there goes unscanned without any error, so the scan fails open.

## What Changes

- The probe syncs its environment with `uv sync --locked --offline`. It then renews the access time
  of every file and directory in the environment, keeping each modification time and never
  following a symlink, and runs the tests with `uv run --no-sync`.
- The gitleaks mirror and the test support's fixture copies use `shutil.copy`, which gives fresh
  times.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: owned temporary resources carry access times from their own attempt.

## Impact

- `src/ethos/adapters/gates/python_quality.py`, `tools/ci/sessions.py`, `tests/conftest.py` and
  `tests/support/runtime_scenarios.py`.
- Tests in `tests/unit/adoption/quality/`.
