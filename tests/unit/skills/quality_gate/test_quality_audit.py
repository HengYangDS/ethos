from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AUDIT_PATH = (
    ROOT / ".agents" / "skills" / "ethos-quality-gate-governance" / "scripts" / "quality_audit.py"
)


def _load_quality_audit() -> object:
    spec = importlib.util.spec_from_file_location("ethos_test_quality_audit", AUDIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_active_concerns_use_current_json_format_owner() -> None:
    audit = _load_quality_audit()

    assert audit.ACTIVE_CONCERNS["json_format"] == "tools/ci/scripts/run-config-lint.sh"
    assert "json_syntax" not in audit.ACTIVE_CONCERNS


def test_quality_audit_uses_the_workspace_runtime_for_public_cli_commands(monkeypatch) -> None:
    audit = _load_quality_audit()
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, '{"ok": true}', "")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)

    assert audit.run_json(ROOT, "quality", "types", "--json") == {"ok": True}
    assert observed["command"] == [
        "uv",
        "run",
        "--all-packages",
        "--group",
        "dev",
        "ethos",
        "quality",
        "types",
        "--json",
    ]


def test_owner_gaps_require_the_ruff_discovery_adapter(tmp_path: Path) -> None:
    """Product quality rejects a missing direct-Ruff discovery boundary."""
    required = [
        "tools/ci/scripts/run-python-lint.sh",
        "tools/ci/scripts/run-python-tests.sh",
        "tools/ci/scripts/run-config-lint.sh",
        "tools/ci/scripts/run-shell-lint.sh",
        "tools/ci/scripts/run-docstring-coverage.sh",
        "tools/ci/scripts/run-module-layout.sh",
        "tools/ci/scripts/run-repository-hygiene.sh",
        ".config/checks/coverage/coverage.ini",
        ".config/checks/coverage/policy.toml",
        ".config/checks/docstrings/policy.toml",
        ".config/checks/module-layout/policy.toml",
        ".config/checks/ty/policy.toml",
        ".config/checks/ruff/ruff.toml",
        ".config/checks/pytest/pytest.ini",
        ".config/checks/taplo/taplo.toml",
        ".config/checks/yaml/yamllint.yaml",
        ".config/checks/shell/.shellcheckrc",
        "system/tools.toml",
    ]
    for relative in required:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n", encoding="utf-8")
    audit = _load_quality_audit()

    gaps = audit.required_file_gaps(tmp_path)

    assert gaps == ["quality_owner_missing:ruff.toml"]


def test_pyproject_policy_gaps_allow_bootstrap_cache_routing(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "sample"

[tool.ruff]
cache-dir = "build/runtime/tool-cache/ruff"

[tool.pytest.ini_options]
cache_dir = "build/runtime/tool-cache/pytest"
""".lstrip(),
        encoding="utf-8",
    )

    audit = _load_quality_audit()

    assert audit.pyproject_policy_gaps(tmp_path) == []


def test_pyproject_policy_gaps_block_real_tool_policy_tables(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "sample"

[tool.ruff]
select = ["E"]

[tool.pytest.ini_options]
addopts = "-q"

[tool.coverage.run]
branch = true

[tool.ty.environment]
python = ".venv"
""".lstrip(),
        encoding="utf-8",
    )

    audit = _load_quality_audit()

    assert audit.pyproject_policy_gaps(tmp_path) == [
        "quality_policy_in_pyproject:[tool.coverage",
        "quality_policy_in_pyproject:[tool.pytest.ini_options].addopts",
        "quality_policy_in_pyproject:[tool.ruff].select",
        "quality_policy_in_pyproject:[tool.ty",
    ]


def test_json_format_is_the_single_catalog_concern() -> None:
    audit = _load_quality_audit()

    assert audit.ACTIVE_CONCERNS["json_format"] == "tools/ci/scripts/run-config-lint.sh"
    assert "json_syntax" not in audit.ACTIVE_CONCERNS
