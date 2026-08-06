from __future__ import annotations

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
    for implicit_command in ('session.run("ethos"', 'session.run("lint-imports"'):
        assert implicit_command not in source
    assert '"-m",\n        "check_jsonschema"' in source


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

    assert gates["ruff"]["command"] == [".venv/bin/nox", "-s", "lint"]
    assert not (ROOT / "tools/ci/scripts/run-python-lint.sh").exists()
    assert not (ROOT / "tools/ci/scripts/run-ruff-ratchet.sh").exists()
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
        "tools/ci/scripts/run-local-ci.sh",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "run-python-lint.sh" not in text
        assert ".venv/bin/nox -s lint" in text


def test_nox_is_the_only_python_test_and_coverage_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    assert gates["unit-architecture"]["command"] == [".venv/bin/nox", "-s", "tests"]
    assert gates["coverage-floor"]["command"] == [
        ".venv/bin/nox",
        "-s",
        "coverage_floor",
    ]
    assert "def tests(" in source
    assert "def coverage_floor(" in source
    assert not (ROOT / "tools/ci/scripts/run-python-tests.sh").exists()


def test_nox_is_the_only_python_build_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["build"]["command"] == [".venv/bin/nox", "-s", "build"]
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv build" not in text
        assert ".venv/bin/nox -s build" in text


def test_nox_is_the_only_local_install_smoke_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["local-install-smoke"]["command"] == [
        ".venv/bin/nox",
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
