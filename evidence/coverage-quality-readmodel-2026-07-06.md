# Coverage Quality Read Model Evidence — 2026-07-06

## Claim

ETHOS exposes the active Python coverage quality floor through a read-only
`ethos quality coverage --json` command while keeping execution ownership in
`.config/ci/scripts/run-python-tests.sh`.

## Mechanism

- Coverage policy owner: `.config/checks/coverage/policy.toml`.
- Coverage tool config owner: `.config/checks/coverage/coverage.ini`.
- Test/coverage execution owner: `.config/ci/scripts/run-python-tests.sh`.
- Read model source: `packages/ethos/src/ethos/repository/policy/coverage.py`.
- CLI projection: `ethos quality coverage --json`.

## Verification

```text
uv run --group dev pytest tests/unit/policy/test_coverage.py tests/unit/cli/test_quality_surface_more.py::test_quality_coverage_reports_policy_and_latest_artifact tests/unit/cli/test_contracts.py::test_quality_help_lists_canonical_commands -q
# 5 passed

uv run --group dev pytest tests/unit/kernel/test_invalid_states.py::test_every_emitted_gap_classifies_to_exactly_one_node -q
# 1 passed

uv run --group dev ruff check packages/ethos/src/ethos/repository/policy/coverage.py packages/ethos/src/ethos/surface/cli/quality.py tests/unit/policy/test_coverage.py tests/unit/cli/test_quality_surface_more.py tests/unit/cli/test_contracts.py tests/unit/kernel/test_invalid_states.py
# All checks passed

uv run --group dev ruff format --check packages/ethos/src/ethos/repository/policy/coverage.py packages/ethos/src/ethos/surface/cli/quality.py tests/unit/policy/test_coverage.py tests/unit/cli/test_quality_surface_more.py tests/unit/cli/test_contracts.py tests/unit/kernel/test_invalid_states.py
# 6 files already formatted

uv run --group dev ty check packages/ethos/src/ethos/repository/policy/coverage.py packages/ethos/src/ethos/surface/cli/quality.py
# All checks passed

.config/ci/scripts/run-python-tests.sh
# 685 passed
# Required test coverage of 95% reached. Total coverage: 95.05%

ETHOS_ROOT=$PWD uv run --group dev ethos quality coverage --json
# ok=true, state=clean, latest_line_percent=96.52, required_gaps=[]
```

## Boundary

`ethos quality coverage` is read-only. It does not run tests and does not make
ignored local coverage artifacts repository truth. The command makes the current
local coverage artifact freshness visible; the owner script remains the proof
producer.

## OpenSpec Archive

- `openspec/changes/archive/2026-07-05-coverage-quality-readmodel`
