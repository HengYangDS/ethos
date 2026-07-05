---
subject: ethos:evidence:docstring-quality-gate
role: evidence
state: active
relations:
  supports: ethos-docstring-quality-gate
---

# Docstring Quality Gate Evidence - 2026-07-05

This evidence records the addition of an ETHOS-owned public-surface docstring
coverage gate.

## Scope

- Added `.config/checks/docstrings/policy.toml` as the docstring policy owner.
- Added `.config/ci/scripts/run-docstring-coverage.sh` as the reusable CI/proof
  script.
- Added `ethos quality docstrings --json` over product-visible Python surfaces.
- Registered the gate in quality profiles, gate registry, `system/tools.toml`,
  and GitLab CI.
- Added missing package-boundary docstrings so the initial public-surface gate
  starts green without forcing private helper docstrings.

## Verification

Commands run from `work/docstring-quality-gate`:

```bash
.config/ci/scripts/run-docstring-coverage.sh
uv run --group dev pytest tests/architecture/test_release_assets.py tests/unit/cli/test_quality_surface_more.py tests/unit/governance/test_validation_gates.py tests/unit/cli/test_contracts.py::test_quality_tool_profiles_command_reports_adapter_boundaries -q
uv run --group dev ruff check packages/ethos/src/ethos/repository/policy/docstrings.py packages/ethos/src/ethos/surface/cli/quality.py packages/ethos/src/ethos/repository/policy/gates.py packages/ethos-core/src/ethos_core/quality/gates.py packages/ethos-core/src/ethos_core/quality/profiles.py tests/architecture/test_release_assets.py tests/unit/cli/test_quality_surface_more.py tests/unit/governance/test_validation_gates.py tests/unit/cli/test_contracts.py
uv run --group dev ruff format --check packages/ethos/src/ethos/repository/policy/docstrings.py packages/ethos/src/ethos/surface/cli/quality.py packages/ethos/src/ethos/repository/policy/gates.py packages/ethos-core/src/ethos_core/quality/gates.py packages/ethos-core/src/ethos_core/quality/profiles.py tests/architecture/test_release_assets.py tests/unit/cli/test_quality_surface_more.py tests/unit/governance/test_validation_gates.py tests/unit/cli/test_contracts.py
uv run --package ethos ethos quality gates --json
.config/ci/scripts/run-python-tests.sh
uv run --group dev ruff check .
uv run --group dev ruff format --check .
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos report --json
```

Observed results:

- Docstring gate: `ok=true`, `coverage_percent=100.0`, `documented_count=101`,
  `public_count=101`.
- Focused tests: `36 passed`.
- Full Python CI gate: `654 passed`, coverage `95.04%`.
- Ruff check: all checks passed.
- Ruff format: `190 files already formatted`.
- Claims: `ok=true`, `state=clean`.
- Report: `ok=true`, `score=16/max_score=16`, `governance_gap_count=0`,
  `parity_pending_count=0`.
- Quality gates: `docstrings` gate appears with command
  `.config/ci/scripts/run-docstring-coverage.sh`.

OpenSpec archive was executed with:

```bash
uv run openspec archive ethos-docstring-quality-gate-20260705 --yes --json
```

Observed archive result: `specsUpdated=true`, one accepted spec updated, and
the carrier moved to `openspec/changes/archive/2026-07-05-ethos-docstring-quality-gate-20260705`.
Executed proof is run after the claim digest is refreshed and the repository
HEAD is finalized.
