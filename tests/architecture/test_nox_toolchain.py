from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_nox_reuses_the_single_locked_project_environment() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    development = project["dependency-groups"]["dev"]

    assert 'nox.options.default_venv_backend = "none"' in source
    assert "session.install(" not in source
    assert "session.run_install(" not in source
    assert any(requirement.startswith("nox>=2026.7.11") for requirement in development)
    assert any(requirement.startswith("uv>=0.12.2") for requirement in development)
    assert "PROJECT_SCRIPTS = Path(sys.executable).parent" in source
    assert 'suffix = ".exe" if os.name == "nt" else ""' in source
    for implicit_command in (
        'session.run("ethos"',
        'session.run("lint-imports"',
        'session.run("ruff"',
        'session.run("uv"',
    ):
        assert implicit_command not in source
    assert 'ruff = _project_script("ruff")' in source
    assert '_project_script("uv"),' in source
    assert '"-m",\n        "check_jsonschema"' in source


def test_python_gate_helpers_bind_project_scripts_instead_of_path() -> None:
    dependency = (ROOT / "tools/ci/dependency_hygiene.py").read_text(encoding="utf-8")
    install = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")

    assert '_project_script("deptry")' in dependency
    assert 'session.run(\n            "deptry"' not in dependency
    assert '_project_script("uv")' in install
    assert '_executable("uv")' not in install


def test_direct_python_dependencies_are_single_current_lower_bounds() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = project["project"]["dependencies"]
    development = [item for group in project["dependency-groups"].values() for item in group]
    build = project["build-system"]["requires"]
    requirements = [*runtime, *development, *build]

    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+>=[^,;\s]+", item) for item in requirements)
    assert "cyclopts>=4.22.5" in runtime
    assert "hatchling>=1.31.0" in development
    assert "hypothesis>=6.165.2" in development
    assert "ty>=0.0.69" in development
    assert build == ["hatchling>=1.31.0"]


def test_locked_tool_resolution_ignores_untrusted_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    for name in ("ruff", "uv", "deptry"):
        executable = tmp_path / name
        executable.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
        executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    import noxfile
    from tools.ci import dependency_hygiene
    from tools.ci import local_install_smoke

    project_scripts = Path(noxfile.sys.executable).parent
    assert Path(noxfile._project_script("ruff")).parent == project_scripts
    assert Path(noxfile._project_script("uv")).parent == project_scripts
    assert Path(dependency_hygiene._project_script("deptry")).parent == project_scripts
    assert Path(local_install_smoke._project_script("uv")).parent == project_scripts


def test_nox_gate_registry_uses_the_bound_python_runtime() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["import-boundaries"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "import_boundaries",
    ]


def test_nox_lint_includes_new_candidate_python_files() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    for option in ("--cached", "--others", "--exclude-standard"):
        assert f'"{option}"' in source


def test_nox_is_the_only_python_lint_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["ruff"]["command"] == ["{python}", "-m", "nox", "-s", "lint"]
    assert not (ROOT / "tools/ci/scripts/run-python-lint.sh").exists()
    assert not (ROOT / "tools/ci/scripts/run-ruff-ratchet.sh").exists()
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "run-python-lint.sh" not in text
        assert "uv run --frozen --offline python -m nox -s lint" in text


def test_nox_is_the_only_python_test_and_coverage_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    assert gates["unit-architecture"]["command"] == ["{python}", "-m", "nox", "-s", "tests"]
    assert gates["coverage-floor"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "coverage_floor",
    ]
    assert "def tests(" in source
    assert "def coverage_floor(" in source
    assert not (ROOT / "tools/ci/scripts/run-python-tests.sh").exists()


def test_nox_is_the_only_python_build_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["build"]["command"] == ["{python}", "-m", "nox", "-s", "build"]
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv build" not in text
        assert "uv run --frozen --offline python -m nox -s build" in text


def test_nox_is_the_only_local_install_smoke_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["local-install-smoke"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "install_smoke",
    ]
    assert not (ROOT / "tools/ci/scripts/run-local-install-smoke.sh").exists()


def test_nox_replaces_cross_platform_python_gate_wrappers() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    sessions = (
        "ci_templates",
        "format_selection",
        "architecture_projection",
        "runbook_registry",
    )
    for session in sessions:
        assert f"def {session}(" in source
    for retired in (
        "run-ci-template-check.sh",
        "run-format-selection.sh",
        "run-architecture-projection-drift.sh",
        "run-runbook-registry-check.sh",
    ):
        assert not (ROOT / "tools/ci/scripts" / retired).exists()
