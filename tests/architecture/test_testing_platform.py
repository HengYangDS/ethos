from __future__ import annotations

import io
import subprocess
import tokenize
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_python_test_platform_is_parallel_timeout_bound_and_owner_scripted() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_deps = "\n".join(pyproject["dependency-groups"]["dev"])
    pytest_ini = (ROOT / ".config/checks/pytest/pytest.ini").read_text(encoding="utf-8")
    script = (ROOT / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")
    policy = tomllib.loads((ROOT / ".config/checks/pytest/policy.toml").read_text(encoding="utf-8"))

    assert "pytest-xdist" in dev_deps
    assert "pytest-timeout" in dev_deps
    assert "tool" not in pyproject or "pytest" not in pyproject["tool"]
    assert "tool" not in pyproject or "ruff" not in pyproject["tool"]
    assert "--strict-config" in pytest_ini
    assert "--strict-markers" in pytest_ini
    assert "required_plugins" in pytest_ini
    assert "pytest-timeout" in pytest_ini
    assert policy["default_workers"] == 8
    assert 'workers="${ETHOS_TEST_WORKERS:-8}"' in script
    assert policy["timeout_seconds"] == 120
    assert policy["default_evidence_root"] == "build/evidence/quality/tests"
    assert "cache_dir = build/runtime/tool-cache/pytest" in pytest_ini
    assert ".config/checks/pytest/.pytest_cache" not in pytest_ini
    assert policy["junit_xml"] == "build/evidence/quality/tests/pytest/junit.xml"
    assert "ETHOS_TEST_WORKERS" in script
    assert "--dist=loadscope" in script
    assert "--junitxml" in script
    assert "--durations" in script
    assert "COVERAGE_FILE" in script
    assert "cleanup_root_coverage_artifacts" in script
    assert "cleanup_denied_runtime_residue" in script
    assert "rm -rf .pytest_cache .ruff_cache" in script
    assert "rm -rf build/runtime/gitlab-ci-local" in script
    assert 'rm -f "${COVERAGE_FILE}" "${COVERAGE_FILE}".*' in script
    assert 'rm -f "${coverage_evidence_dir}/coverage.xml"' in script
    assert ".coverage.*" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "junit.xml" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_python_test_gate_serializes_shared_coverage_evidence_writes() -> None:
    script = (ROOT / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")

    assert "coverage_lock_dir" in script
    assert 'mkdir "${coverage_lock_dir}"' in script
    assert 'rmdir "${coverage_lock_dir}"' in script
    assert "waiting for coverage evidence lock" in script
    assert "coverage evidence writes are serialized" in script


def test_python_test_gate_can_shard_without_lowering_coverage_floor() -> None:
    script = (ROOT / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")

    assert "ETHOS_TEST_SHARDS" in script
    assert "collect-only" in script
    assert "coverage combine" in script
    assert "coverage xml" in script
    assert "coverage report" in script
    assert "shard_passed_marker" in script
    assert "reusing completed pytest shard" in script
    assert "ethos_python_test_head" in script
    assert "shard_plan_key" in script
    assert 'printf \'%s\\n\' "${shard_plan_key}" > "${shard_head_path}"' in script
    assert 'printf \'%s\\n\' "${shard_plan_key}" > "${shard_passed_marker}"' in script
    assert '--fail-under="${coverage_hard_floor}"' in script
    assert "--cov-fail-under=0" in script
    assert "--cov-fail-under=${coverage_hard_floor}" in script


def test_python_test_gate_fails_closed_when_head_changes_during_run() -> None:
    script = (ROOT / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")

    assert "tools/ci/scripts/require-stable-head.sh capture" in script
    assert "tools/ci/scripts/require-stable-head.sh verify" in script
    assert "_ethos_verify_python_test_head_stability" in script
    assert "trap cleanup_and_release EXIT" in script


def test_performance_and_report_mechanisms_have_declared_boundaries() -> None:
    tools = tomllib.loads((ROOT / "system/tools.toml").read_text(encoding="utf-8"))["tool"]
    by_concern = {tool["concern"]: tool for tool in tools}

    assert by_concern["tests"]["gate"] == "tools/ci/scripts/run-python-tests.sh"
    assert (
        by_concern["tests"]["config"]
        == ".config/checks/pytest/pytest.ini + .config/checks/pytest/policy.toml"
    )
    assert by_concern["tests"]["artifacts"] == "build/evidence/quality/tests/"
    assert by_concern["test_performance"]["gate"] == "ethos quality performance --json"
    assert by_concern["test_performance"]["config"] == ".config/checks/performance/policy.toml"
    assert by_concern["test_performance"]["artifacts"] == "build/evidence/quality/performance/"
    assert by_concern["test_reporting"]["planned"] is True


def test_performance_evidence_is_head_bound_and_local_only() -> None:
    policy = tomllib.loads(
        (ROOT / ".config/checks/performance/policy.toml").read_text(encoding="utf-8")
    )
    script = (ROOT / "tools/ci/scripts/run-performance-evidence.sh").read_text(encoding="utf-8")

    assert policy["samples"] == 5
    assert policy["latest_path"] == "build/evidence/quality/performance/latest.json"
    assert policy["baseline_path"] == "build/evidence/quality/performance/baseline.json"
    assert "require-stable-head.sh capture" in script
    assert "require-stable-head.sh verify" in script
    assert "cold_subprocess_and_hot_inprocess_samples" in script
    assert "--accept-baseline" in script
    assert "token_estimate" in script


def test_runtime_artifacts_do_not_live_under_config_check_owners() -> None:
    script = (ROOT / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")
    assert ".config/checks/pytest/junit.xml" not in script
    assert ".config/checks/pytest/.pytest_cache" not in script
    assert ".config/checks/coverage/coverage.xml" not in script
    assert "build/evidence/quality/tests" in script
    assert "ETHOS_TEST_BASETEMP" in script
    assert "ethos-pytest" in script


def test_python_test_gate_isolates_worker_local_proof_state() -> None:
    conftest = (ROOT / "tests/conftest.py").read_text(encoding="utf-8")

    assert "ETHOS_TEST_PROOF_STATE_DIR" in conftest
    assert "PYTEST_XDIST_WORKER" in conftest
    assert "proof-{worker}" in conftest


def test_repository_hygiene_gate_is_owner_scripted_and_projected() -> None:
    script = (ROOT / "tools/ci/scripts/run-repository-hygiene.sh").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    tools = tomllib.loads((ROOT / "system/tools.toml").read_text(encoding="utf-8"))["tool"]
    by_concern = {tool["concern"]: tool for tool in tools}

    assert '"git", "ls-files"' in script
    assert "possible merge conflict marker" in script
    assert "tools/ci/scripts/run-repository-hygiene.sh" in gitlab
    assert "tools/ci/scripts/run-repository-hygiene.sh" in precommit
    assert by_concern["repository_hygiene"]["gate"] == "tools/ci/scripts/run-repository-hygiene.sh"


def test_product_boundary_gate_is_owner_scripted_and_projected() -> None:
    script = (ROOT / "tools/ci/scripts/run-product-boundary.sh").read_text(encoding="utf-8")
    local_ci = (ROOT / "tools/ci/scripts/run-local-ci.sh").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    tools = tomllib.loads((ROOT / "system/tools.toml").read_text(encoding="utf-8"))["tool"]
    by_concern = {tool["concern"]: tool for tool in tools}

    assert "ethos.cli quality" in script
    assert "run_ethos_quality product-boundary" in script
    assert "run_ethos_quality contributor-policy" in script
    assert "uv run --all-packages --group dev" not in script
    assert "active product surfaces and release metadata neutral" in script
    assert "tools/ci/scripts/run-product-boundary.sh" in local_ci
    assert "tools/ci/scripts/run-product-boundary.sh" in gitlab
    assert "tools/ci/scripts/run-product-boundary.sh" in precommit
    assert by_concern["product_boundary"]["gate"] == "tools/ci/scripts/run-product-boundary.sh"


def test_governance_kernel_gate_uses_local_command_plane_without_dev_env_sync() -> None:
    script = (ROOT / "tools/ci/scripts/run-governance-kernel.sh").read_text(encoding="utf-8")

    assert "ethos.cli quality governance-kernel" in script
    assert "ETHOS_PYTHON" in script
    assert "PYTHONPATH" in script
    assert "uv run --all-packages --group dev" not in script


def test_python_lint_gate_discovers_every_tracked_python_source() -> None:
    """Every tracked Python file is governed by one lint/format law."""
    script = (ROOT / "tools/ci/scripts/run-python-lint.sh").read_text(encoding="utf-8")

    assert "git ls-files" in script
    assert "*.py" in script
    assert "*.pyi" in script
    assert "python_quality_paths" in script
    assert "no tracked Python files found for Ruff" in script
    assert "packages/tools/tests are required" in script
    assert "not sufficient" in script
    assert (
        'ruff check --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" "${python_quality_paths[@]}"'
        in script
    )
    assert (
        'ruff format --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" --check "${python_quality_paths[@]}"'
        in script
    )


def test_python_lint_gate_has_no_tracked_python_side_lanes() -> None:
    tracked = {
        line.strip()
        for line in subprocess.check_output(
            ["git", "ls-files", "*.py", "*.pyi"], cwd=ROOT, text=True
        ).splitlines()
        if line.strip()
    }
    script = (ROOT / "tools/ci/scripts/run-python-lint.sh").read_text(encoding="utf-8")

    assert tracked
    assert 'mapfile -t python_quality_paths < <(git ls-files "*.py" "*.pyi")' in script
    assert any(path.startswith(".agents/") for path in tracked)


def test_python_sast_gate_discovers_every_tracked_python_source() -> None:
    """Every tracked Python file is governed by one SAST law."""
    script = (ROOT / "tools/ci/scripts/run-bandit.sh").read_text(encoding="utf-8")

    assert 'mapfile -t python_security_paths < <(git ls-files "*.py")' in script
    assert "no tracked Python files found for Bandit" in script
    assert "${python_security_paths[@]}" in script
    assert "-r packages" not in script


def test_python_sast_gate_has_no_local_suppression_surface() -> None:
    """Bandit should govern Python without local suppressions or skipped rules."""
    tracked = [
        line.strip()
        for line in subprocess.check_output(["git", "ls-files", "*.py"], cwd=ROOT, text=True)
        .strip()
        .splitlines()
        if line.strip()
    ]
    bandit_config = (ROOT / ".config/checks/bandit/bandit.yaml").read_text(encoding="utf-8")
    nosec_offenders = [
        path
        for path in tracked
        if _python_comments_contain((ROOT / path).read_text(encoding="utf-8"), "nosec")
    ]

    assert nosec_offenders == []
    assert "skips:\n  []" in bandit_config
    assert "B404" not in bandit_config
    assert "B603" not in bandit_config
    assert "B608" not in bandit_config


def _python_comments_contain(source: str, needle: str) -> bool:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return any(token.type == tokenize.COMMENT and needle in token.string for token in tokens)
