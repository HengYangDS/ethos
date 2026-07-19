from __future__ import annotations

import importlib.util
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
