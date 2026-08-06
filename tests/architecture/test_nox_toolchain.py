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
