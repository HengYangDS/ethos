from __future__ import annotations

import json
import re
import sys
import tempfile
import tomllib
from pathlib import Path

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tools.ci.python_test_gate import PYTHON
from tools.ci.python_test_gate import PythonTestGate
from tools.ci.python_test_gate import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_nox_reuses_the_single_locked_project_environment() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    development = project["dependency-groups"]["dev"]

    assert 'nox.options.default_venv_backend = "none"' in source
    assert any(requirement.startswith("nox>=2026.7.11") for requirement in development)
    assert any(requirement.startswith("uv>=0.12.2") for requirement in development)
    assert "PROJECT_SCRIPTS = Path(sys.executable).parent" in source
    assert 'suffix = ".exe" if os.name == "nt" else ""' in source
    assert 'ruff = _project_script("ruff")' in source
    assert '_project_script("uv"),' in source
    assert '"-m",\n        "check_jsonschema"' in source


def test_python_gate_helpers_bind_project_scripts_instead_of_path() -> None:
    dependency = (ROOT / "tools/ci/dependency_hygiene.py").read_text(encoding="utf-8")
    install = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")

    assert '_project_script("deptry")' in dependency
    assert '_project_script("uv")' in install


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


def test_self_hosted_nox_gates_bind_the_repository_locked_python(monkeypatch) -> None:
    package_python = ROOT / "build/runtime/package-only/bin/python"
    monkeypatch.setattr("ethos.repository.policy.gates.sys.executable", package_python.as_posix())
    policy = resolve_gate_policy(ROOT, tree_ref="HEAD", gate_ids=("ruff",))

    assert policy.registry["ruff"].command[:3] == (
        (ROOT / ".venv/bin/python").as_posix(),
        "-m",
        "nox",
    )
    assert {path for path, _digest in policy.sources[0][1]} == {
        "noxfile.py",
        "pyproject.toml",
        "uv.lock",
    }


def test_nox_lint_includes_new_candidate_python_files() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    for option in ("--cached", "--others", "--exclude-standard"):
        assert f'"{option}"' in source


def test_nox_is_the_only_python_lint_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert gates["ruff"]["command"] == ["{python}", "-m", "nox", "-s", "lint"]
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv run --frozen --offline python -m nox -s format_check" in text
        assert "uv run --frozen --offline python -m nox -s lint" not in text


def test_nox_exposes_explicit_ruff_format_without_mutating_lint() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    format_body = source[source.index("def format_repository(") : source.index("def lint(")]
    lint_body = source[source.index("def lint(") : source.index("def tests(")]
    assert '_project_script("ruff"), "format", *common, *paths' in format_body
    assert 'ruff, "format", *common, "--check", *paths' in lint_body
    assert '"--fix"' not in lint_body


def test_nox_exposes_one_all_carrier_format_and_read_only_check() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    format_body = source[source.index("def format_repository(") : source.index("def lint(")]
    check_body = source[source.index("def format_check(") : source.index("def tests(")]
    for operation in (
        "_format_config",
        "_format_markdown",
        "_format_shell",
        "_format_javascript",
        "_format_svg",
    ):
        assert operation in format_body
    for check in (
        "lint(session)",
        "config_quality(session)",
        "markdown_lint(session)",
        "shell_lint(session)",
        "javascript_lint(session)",
        "svg_lint(session)",
        "asset_validation(session)",
    ):
        assert check in check_body


def test_wheel_build_materializes_only_the_openspec_production_closure() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert manifest["dependencies"] == {"@fission-ai/openspec": "1.8.0"}
    assert "@fission-ai/openspec" not in manifest["devDependencies"]
    assert '"ETHOS_BUILD_NODE": str(NODE)' in source
    assert '"ETHOS_BUILD_NPM_CLI": str(' in source
    hook = (ROOT / "tools/ci/openspec_runtime_hook.py").read_text(encoding="utf-8")
    assert '"ci"' in hook
    assert '"--omit=dev"' in hook
    assert '"--offline"' in hook
    assert 'tempfile.mkdtemp(prefix="ethos-openspec-supply-")' in hook


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
        assert "uv run --frozen --offline python -m nox -s build" in text


def test_nox_is_the_only_local_install_smoke_orchestrator() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    assert "def prepare_install_supply(" in source
    assert gates["local-install-smoke"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "install_smoke",
    ]


def test_nox_owns_cross_platform_python_gate_sessions() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    sessions = (
        "ci_templates",
        "format_selection",
        "architecture_projection",
        "runbook_registry",
    )
    for session in sessions:
        assert f"def {session}(" in source


def test_nox_is_the_only_prose_orchestrator() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    declaration = tomllib.loads((ROOT / "system/tools.toml").read_text(encoding="utf-8"))
    tools = {tool["concern"]: tool for tool in declaration["tool"]}

    assert "def prose(" in source
    assert '_project_script("codespell")' in source
    assert tools["prose"]["gate"] == "uv run --frozen --offline python -m nox -s prose"
    assert not (ROOT / "tools/ci/scripts/run-prose-check.sh").exists()
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv run --frozen --offline python -m nox -s prose" in text
        assert "run-prose-check.sh" not in text


def test_nox_is_the_only_shell_lint_orchestrator() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert "def shell_lint(" in source
    assert '_project_script("shellcheck")' in source
    assert "shellcheck-py>=0.11.0.1" in project["dependency-groups"]["dev"]
    assert gates["shell-lint"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "shell_lint",
    ]
    assert not (ROOT / "tools/ci/scripts/run-shell-lint.sh").exists()
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv run --frozen --offline python -m nox -s format_check" in text
        assert "uv run --frozen --offline python -m nox -s shell_lint" not in text
        assert "run-shell-lint.sh" not in text


def test_nox_is_the_only_markdown_lint_orchestrator() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    node_package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert "def markdown_lint(" in source
    assert 'NODEJS_WHEEL = Path(import_module("nodejs_wheel").__file__).resolve().parent' in source
    assert 'NODEJS_WHEEL / "bin" / ("node.exe" if os.name == "nt" else "node")' in source
    assert 'ROOT / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"' in source
    assert package["project"]["requires-python"] == ">=3.12"
    assert node_package["devDependencies"]["markdownlint-cli2"] == "0.23.2"
    assert all("markdownlint" not in command for command in node_package["scripts"].values())
    assert not (ROOT / "tools/ci/scripts/run-markdown-lint.sh").exists()
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv run --frozen --offline python -m nox -s format_check" in text
        assert "uv run --frozen --offline python -m nox -s markdown_lint" not in text
        assert "run-markdown-lint.sh" not in text


def test_nox_is_the_only_configuration_quality_orchestrator() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    owner = (ROOT / "tools/ci/config_quality.py").read_text(encoding="utf-8")
    package = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    node_package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert "def config_quality(" in source
    assert 'import_module("tools.ci.config_quality").run' in source
    assert "from yamllint import linter as yamllint_linter" in owner
    assert 'ROOT / "node_modules/@taplo/cli/dist/cli.js"' in owner
    assert "yamllint>=1.38.0" in package["dependency-groups"]["dev"]
    assert node_package["devDependencies"]["@taplo/cli"] == "0.7.0"
    assert not (ROOT / "tools/ci/scripts/run-config-lint.sh").exists()
    assert not (ROOT / "tools/ci/scripts/install-taplo.sh").exists()
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "uv run --frozen --offline python -m nox -s config_quality" in pre_commit
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv run --frozen --offline python -m nox -s format_check" in text
        assert "uv run --frozen --offline python -m nox -s config_quality" not in text
        assert "run-config-lint.sh" not in text


def test_nox_is_the_only_hosted_observation_orchestrator() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    assert "def hosted_observation(" in source
    assert 'import_module("tools.ci.hosted_observation").capture_observation' in source
    assert not (ROOT / "tools/ci/scripts/run-hosted-provider-observation.sh").exists()
    for relative in (
        ".config/ci/templates/hosted/github-actions.yml",
        ".config/ci/templates/hosted/gitlab-ci.yml",
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "uv run --frozen --offline python -m nox -s hosted_observation" in text
        assert "run-hosted-provider-observation.sh" not in text


def test_nox_host_conformance_reuses_build_install_and_portable_tests() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")

    assert "def host_conformance(" in source
    assert "_build_wheel(session)" in source
    assert "prepare_install_supply(session)" in source
    assert "run_install_smoke(session)" in source
    assert '"tests/architecture/test_portable_toolchain.py"' in source
    assert '"tests/architecture/test_local_install_smoke.py"' in source


def test_python_test_gate_uses_portable_runtime_paths_and_lock(tmp_path: Path) -> None:
    gate = PythonTestGate(
        Settings(
            head="0" * 40,
            evidence=tmp_path / "evidence",
            basetemp=tmp_path / "pytest",
            workers=None,
            shards=None,
            durations=1,
            timeout=None,
            lock_wait=1,
            identity=None,
        )
    )
    source = (ROOT / "tools/ci/python_test_gate.py").read_text(encoding="utf-8")

    assert Path(sys.executable) == PYTHON
    assert gate.identity_home.parent == Path(tempfile.gettempdir())
    assert "FileLock" in source
    assert '"GIT_CONFIG_GLOBAL": os.devnull' in source
    assert "_process_start" not in source
    assert 'ROOT / ".venv/bin/python"' not in source
    assert 'os.getenv("TMPDIR", "/tmp")' not in source
