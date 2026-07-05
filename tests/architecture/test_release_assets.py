from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitlab_visible_project_files_exist() -> None:
    required = {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
    }

    files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}

    assert required <= files


def test_contributing_declares_commit_and_signature_policy() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "Conventional Commits" in text
    assert "SSH signing" in text
    assert "Yang HENG <heng.yang.ds@hotmail.com>" in text


def test_gitlab_ci_uses_ethos_public_command_plane() -> None:
    text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "ethos audit" in text
    assert "ethos report" in text
    assert "image: node:24" in text
    assert "npm config set engine-strict true" in text
    assert "npm ci --ignore-scripts" in text
    assert "npm run ethos -- --version" in text
    assert "npm run test:npm" in text
    assert "uv run --group dev pytest tests/unit tests/architecture -q" in text
    assert ".config/ci/scripts/bootstrap-python.sh" in text
    assert ".config/ci/scripts/install-lychee.sh" in text
    assert ".config/ci/scripts/run-import-linter.sh" in text
    assert (
        "uv run --group dev lint-imports --config .config/checks/import-linter/contracts.ini"
        not in text
    )
    assert "uv run --no-project --with import-linter lint-imports" not in text
    assert "pip install uv" not in text
    assert "curl -sSL https://github.com/lycheeverse/lychee" not in text
    assert "wt " not in text
    assert "proof " not in text


def test_configuration_layout_is_separated_by_concern() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ruff = (ROOT / "ruff.toml").read_text(encoding="utf-8")
    pytest = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    config_readme = (ROOT / ".config/README.md").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "[project]" in pyproject
    assert "[tool.uv.workspace]" in pyproject
    assert "[tool.pytest" not in pyproject
    assert "[tool.ruff" not in pyproject
    assert 'extend = ".config/checks/ruff/ruff.toml"' in ruff
    assert "[lint.per-file-ignores]" in ruff
    assert "[pytest]" in pytest
    assert "pythonpath" in pytest
    assert "Separation of concerns" in config_readme
    assert "system/tools.toml" in config_readme
    assert 'config = "pytest.ini"' in tools
    assert 'config = "ruff.toml + .config/checks/ruff/"' in tools
    assert 'config = ".config/checks/import-linter/"' in tools
    assert 'config = ".config/checks/lychee/"' in tools
    assert 'config = ".config/boundaries/"' not in tools
    assert 'config = ".config/docs/lychee.toml"' not in tools
    assert (ROOT / ".config/ci/scripts/bootstrap-python.sh").exists()
    assert (ROOT / ".config/ci/scripts/install-lychee.sh").exists()
    assert (ROOT / ".config/ci/scripts/run-import-linter.sh").exists()


def test_ci_lychee_installer_is_architecture_aware() -> None:
    installer = (ROOT / ".config/ci/scripts/install-lychee.sh").read_text(encoding="utf-8")

    assert "uname -m" in installer
    assert "aarch64-unknown-linux-gnu" in installer
    assert "x86_64-unknown-linux-gnu" in installer
    assert "find" in installer
    assert "LYCHEE_VERSION" in installer
    assert "--retry" in installer
    assert "--retry-all-errors" in installer
    assert "--max-time" in installer
    assert "command -v lychee" in installer
    assert "tar xz -C /usr/local/bin lychee" not in installer
