from __future__ import annotations

import json
import re
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tools.ci.python_test_gate import PYTHON
from tools.ci.python_test_gate import PythonTestGate
from tools.ci.python_test_gate import Settings

ROOT = Path(__file__).resolve().parents[2]
HOSTED_PROJECTIONS = (
    ".config/ci/templates/hosted/github-actions.yml",
    ".config/ci/templates/hosted/gitlab-ci.yml",
    ".github/workflows/ci.yml",
    ".gitlab-ci.yml",
)


def _nox() -> str:
    return (ROOT / "noxfile.py").read_text(encoding="utf-8")


def _gates() -> dict[str, dict[str, object]]:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    return {gate["id"]: gate for gate in declaration["gates"]}


def _assert_hosted(command: str, *, present: bool) -> None:
    for relative in HOSTED_PROJECTIONS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert (command in text) is present


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
    source = _nox()

    for option in ("--cached", "--others", "--exclude-standard"):
        assert f'"{option}"' in source


def test_nox_is_the_only_python_lint_orchestrator() -> None:
    assert _gates()["ruff"]["command"] == ["{python}", "-m", "nox", "-s", "lint"]
    _assert_hosted("uv run --frozen --offline python -m nox -s format_check", present=True)
    _assert_hosted("uv run --frozen --offline python -m nox -s lint", present=False)


def test_nox_exposes_explicit_ruff_format_without_mutating_lint() -> None:
    source = _nox()

    format_body = source[source.index("def format_repository(") : source.index("def lint(")]
    lint_body = source[source.index("def lint(") : source.index("def tests(")]
    assert '_project_script("ruff"), "format", *common, *paths' in format_body
    assert 'ruff, "format", *common, "--check", *paths' in lint_body
    assert '"--fix"' not in lint_body


def test_nox_exposes_one_all_carrier_format_and_read_only_check() -> None:
    source = _nox()

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
    gates, source = _gates(), _nox()

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
    assert _gates()["build"]["command"] == ["{python}", "-m", "nox", "-s", "build"]
    _assert_hosted("uv run --frozen --offline python -m nox -s build", present=True)


def test_nox_is_the_only_local_install_smoke_orchestrator() -> None:
    gates, source = _gates(), _nox()

    assert "def prepare_install_supply(" in source
    assert gates["local-install-smoke"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "install_smoke",
    ]


def test_nox_owns_cross_platform_python_gate_sessions() -> None:
    source = _nox()
    sessions = (
        "ci_templates",
        "format_selection",
        "architecture_projection",
        "runbook_registry",
    )
    for session in sessions:
        assert f"def {session}(" in source


@pytest.mark.parametrize(
    ("session", "owned_tokens", "absent_scripts", "hosted", "hosted_mode"),
    [
        (
            "prose",
            ('_project_script("codespell")',),
            ("run-prose-check.sh",),
            "uv run --frozen --offline python -m nox -s prose",
            "present",
        ),
        (
            "shell_lint",
            ('_project_script("shellcheck")',),
            ("run-shell-lint.sh",),
            "uv run --frozen --offline python -m nox -s shell_lint",
            "absent",
        ),
        (
            "markdown_lint",
            (
                'NODEJS_WHEEL = Path(import_module("nodejs_wheel").__file__).resolve().parent',
                'ROOT / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"',
            ),
            ("run-markdown-lint.sh",),
            "uv run --frozen --offline python -m nox -s markdown_lint",
            "absent",
        ),
        (
            "config_quality",
            ('import_module("tools.ci.config_quality").run',),
            ("run-config-lint.sh", "install-taplo.sh"),
            "uv run --frozen --offline python -m nox -s config_quality",
            "absent",
        ),
        (
            "hosted_observation",
            ('import_module("tools.ci.hosted_observation").capture_observation',),
            ("run-hosted-provider-observation.sh",),
            "uv run --frozen --offline python -m nox -s hosted_observation",
            "present",
        ),
    ],
)
def test_nox_is_the_only_declared_quality_orchestrator(
    session: str,
    owned_tokens: tuple[str, ...],
    absent_scripts: tuple[str, ...],
    hosted: str,
    hosted_mode: str,
) -> None:
    source = _nox()
    assert f"def {session}(" in source
    assert all(token in source for token in owned_tokens)
    assert all(not (ROOT / "tools/ci/scripts" / script).exists() for script in absent_scripts)
    _assert_hosted(hosted, present=hosted_mode == "present")


def test_quality_orchestrator_toolchain_is_declared_once() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    dev = project["dependency-groups"]["dev"]
    assert "shellcheck-py>=0.11.0.1" in dev
    assert "yamllint>=1.38.0" in dev
    assert package["devDependencies"] | {
        "requires-python": project["project"]["requires-python"]
    } == {
        **package["devDependencies"],
        "requires-python": ">=3.12",
    }
    assert package["devDependencies"]["markdownlint-cli2"] == "0.23.2"
    assert package["devDependencies"]["@taplo/cli"] == "0.7.0"
    owner = (ROOT / "tools/ci/config_quality.py").read_text(encoding="utf-8")
    assert "from yamllint import linter as yamllint_linter" in owner
    assert 'ROOT / "node_modules/@taplo/cli/dist/cli.js"' in owner
    pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "uv run --frozen --offline python -m nox -s config_quality" in pre_commit


def test_nox_host_conformance_reuses_build_install_and_portable_tests() -> None:
    source = _nox()

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
