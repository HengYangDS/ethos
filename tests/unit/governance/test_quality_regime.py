from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED_OR_LOCAL_ROOTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
}


def test_ci_quality_stage_invokes_config_and_shell_owner_scripts() -> None:
    ci = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "ethos:config:" in ci
    assert "ethos:shell:" in ci
    assert "- tools/ci/scripts/run-config-lint.sh" in ci
    assert "- tools/ci/scripts/run-shell-lint.sh" in ci
    assert "taplo" not in ci
    assert "yamllint" not in ci
    assert "shellcheck" not in ci


def test_config_quality_has_dedicated_policy_not_pyproject_dumping_ground() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    config_readme = (ROOT / ".config" / "README.md").read_text(encoding="utf-8")

    assert "[tool.ruff" not in pyproject
    assert "[tool.pytest" not in pyproject
    assert "[tool.coverage" not in pyproject
    assert "[tool.taplo" not in pyproject
    assert ".config/checks/taplo/taplo.toml" in config_readme
    assert ".config/checks/yaml/yamllint.yaml" in config_readme
    assert ".config/checks/shell/.shellcheckrc" in config_readme


def test_toml_files_have_exactly_one_final_newline_and_no_trailing_space() -> None:
    bad: list[str] = []
    for path in sorted(ROOT.rglob("*.toml")):
        if any(part in GENERATED_OR_LOCAL_ROOTS for part in path.relative_to(ROOT).parts):
            continue
        data = path.read_bytes()
        if data and not data.endswith(b"\n"):
            bad.append(f"{path.relative_to(ROOT)}:missing-final-newline")
        if data.endswith(b"\n\n"):
            bad.append(f"{path.relative_to(ROOT)}:extra-trailing-newline")
        for index, line in enumerate(data.splitlines(), start=1):
            if line.rstrip(b" \t") != line:
                bad.append(f"{path.relative_to(ROOT)}:{index}:trailing-space")

    assert bad == []


def test_pytest_runtime_cache_stays_out_of_config_plane() -> None:
    pytest_ini = (ROOT / "pytest.ini").read_text(encoding="utf-8")

    assert "cache_dir = build/runtime/tool-cache/pytest" in pytest_ini
    assert "cache_dir = .config/checks/pytest" not in pytest_ini
    assert not (ROOT / ".config" / "checks" / "pytest" / ".gitignore").exists()


def test_tool_catalog_marks_config_gates_active_with_owner_scripts() -> None:
    tools = (ROOT / "system" / "tools.toml").read_text(encoding="utf-8")

    assert re.search(
        r'concern = "toml"[\s\S]*?config = "\.config/checks/taplo/taplo\.toml"[\s\S]*?gate = "tools/ci/scripts/run-config-lint\.sh"',
        tools,
    )
    assert re.search(
        r'concern = "yaml"[\s\S]*?config = "\.config/checks/yaml/yamllint\.yaml"[\s\S]*?gate = "tools/ci/scripts/run-config-lint\.sh"',
        tools,
    )
    assert re.search(
        r'concern = "shell"[\s\S]*?config = "\.config/checks/shell/\.shellcheckrc"[\s\S]*?gate = "tools/ci/scripts/run-shell-lint\.sh"',
        tools,
    )
