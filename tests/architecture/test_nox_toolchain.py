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
from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]
HOSTED = (
    ".config/ci/templates/hosted/github-actions.yml",
    ".config/ci/templates/hosted/gitlab-ci.yml",
    ".github/workflows/ci.yml",
    ".gitlab-ci.yml",
)


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _gates() -> dict[str, dict[str, object]]:
    return {gate["id"]: gate for gate in tomllib.loads(_text("system/gates.toml"))["gates"]}


def _hosted(command: str, *, present: bool) -> None:
    assert all((command in _text(path)) is present for path in HOSTED)


def test_locked_runtime_and_direct_dependencies_are_singular() -> None:
    source, project = _text("noxfile.py"), tomllib.loads(_text("pyproject.toml"))
    requirements = [
        *project["project"]["dependencies"],
        *(item for group in project["dependency-groups"].values() for item in group),
        *project["build-system"]["requires"],
    ]
    assert 'nox.options.default_venv_backend = "none"' in source
    assert "RUNTIME = ProjectRuntime.discover(ROOT)" in source
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+>=[^,;\s]+", item) for item in requirements)
    assert project["build-system"]["requires"] == ["hatchling>=1.31.0"]
    for requirement in ("nox>=2026.7.11", "uv>=0.12.2", "ty>=0.0.69"):
        assert requirement in project["dependency-groups"]["dev"]


def test_project_runtime_is_cross_platform_and_fails_closed(tmp_path: Path) -> None:
    source = _text("tools/ci/toolchain/environment.py")
    runtime = ProjectRuntime(tmp_path, tmp_path / "python", tmp_path / "bin")
    assert 'suffix = ".exe" if os.name == "nt" else ""' in source
    with pytest.raises(RuntimeError, match="project executable is unavailable"):
        runtime.script("uv")


def test_gate_helpers_consume_the_single_runtime_owner() -> None:
    nox, dependency, install = map(
        _text,
        ("noxfile.py", "tools/ci/dependency_hygiene.py", "tools/ci/local_install_smoke.py"),
    )
    for source, executable in ((nox, "ruff"), (dependency, "deptry"), (install, "uv")):
        assert f'RUNTIME.script("{executable}")' in source
    assert "def _project_script(" not in nox + dependency + install


def test_nox_sessions_are_the_declared_gate_owners() -> None:
    gates, source = _gates(), _text("noxfile.py")
    expected = {
        "ruff": "lint",
        "unit-architecture": "tests",
        "coverage-floor": "coverage_floor",
        "build": "build",
        "local-install-smoke": "install_smoke",
        "import-boundaries": "import_boundaries",
    }
    for gate, session in expected.items():
        assert gates[gate]["command"] == ["{python}", "-m", "nox", "-s", session]
        assert f"def {session}(" in source
    _hosted("uv run --frozen --offline python -m nox -s format_check", present=True)
    _hosted("uv run --frozen --offline python -m nox -s build", present=True)
    _hosted("uv run --frozen --offline python -m nox -s lint", present=False)


def test_self_hosted_gate_binds_the_worktree_python(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ethos.repository.policy.gates.sys.executable",
        (ROOT / "build/runtime/package-only/bin/python").as_posix(),
    )
    policy = resolve_gate_policy(ROOT, tree_ref="HEAD", gate_ids=("ruff",))
    assert policy.registry["ruff"].command[:3] == (
        (ROOT / ".venv/bin/python").as_posix(),
        "-m",
        "nox",
    )
    assert {path for path, _ in policy.sources[0][1]} == {"noxfile.py", "pyproject.toml", "uv.lock"}


def test_lint_and_format_cover_candidates_without_mutation() -> None:
    source = _text("noxfile.py")
    for option in ("--cached", "--others", "--exclude-standard"):
        assert f'"{option}"' in source
    format_body = source[source.index("def format_repository(") : source.index("def lint(")]
    lint_body = source[source.index("def lint(") : source.index("def javascript_lint(")]
    assert 'RUNTIME.script("ruff"), "format"' in format_body
    assert 'ruff, "format", *common, "--check"' in lint_body
    assert '"--fix"' not in lint_body


def test_all_carrier_format_closure_is_explicit() -> None:
    source = _text("noxfile.py")
    write = source[source.index("def format_repository(") : source.index("def lint(")]
    read = source[source.index("def format_check(") : source.index("def tests(")]
    assert all(
        f"_format_{name}" in write for name in ("config", "markdown", "shell", "javascript", "svg")
    )
    assert all(
        f"{name}(session)" in read
        for name in (
            "lint",
            "config_quality",
            "markdown_lint",
            "shell_lint",
            "javascript_lint",
            "svg_lint",
            "asset_validation",
        )
    )


def test_delivery_pipeline_owns_offline_build_and_package_conformance() -> None:
    nox, delivery = _text("noxfile.py"), _text("tools/ci/delivery/pipeline.py")
    manifest = json.loads(_text("package.json"))
    assert manifest["dependencies"] == {"@fission-ai/openspec": "1.8.0"}
    assert "DELIVERY = DeliveryPipeline.from_runtime(RUNTIME)" in nox
    assert "DELIVERY.prove_host(session)" in nox
    for token in (
        'self.runtime.script("uv")',
        '"--offline"',
        '"ETHOS_BUILD_NODE"',
        "self.prepare_supply()",
        "self.prove_install(session)",
        '"tests/architecture/test_portable_toolchain.py"',
        '"tests/architecture/test_local_install_smoke.py"',
    ):
        assert token in delivery
    hook = _text("tools/ci/openspec_runtime_hook.py")
    assert all(token in hook for token in ('"ci"', '"--omit=dev"', '"--offline"'))


@pytest.mark.parametrize(
    ("session", "owner", "removed", "hosted"),
    [
        ("prose", 'RUNTIME.script("codespell")', "run-prose-check.sh", True),
        ("shell_lint", 'RUNTIME.script("shellcheck")', "run-shell-lint.sh", False),
        ("markdown_lint", "NODE = DELIVERY.node", "run-markdown-lint.sh", False),
        (
            "config_quality",
            'import_module("tools.ci.config_quality").run',
            "run-config-lint.sh",
            False,
        ),
        (
            "hosted_observation",
            'import_module("tools.ci.hosted_observation").capture_observation',
            "run-hosted-provider-observation.sh",
            True,
        ),
    ],
)
def test_quality_sessions_have_one_owner(
    session: str, owner: str, removed: str, *, hosted: bool
) -> None:
    source = _text("noxfile.py")
    assert f"def {session}(" in source
    assert owner in source
    assert not (ROOT / "tools/ci/scripts" / removed).exists()
    _hosted(f"uv run --frozen --offline python -m nox -s {session}", present=hosted)


def test_toolchain_versions_and_native_config_have_one_declaration() -> None:
    project, package = tomllib.loads(_text("pyproject.toml")), json.loads(_text("package.json"))
    dev = project["dependency-groups"]["dev"]
    assert {"shellcheck-py>=0.11.0.1", "yamllint>=1.38.0"} <= set(dev)
    assert package["devDependencies"]["markdownlint-cli2"] == "0.23.2"
    assert package["devDependencies"]["@taplo/cli"] == "0.7.0"
    assert "from yamllint import linter as yamllint_linter" in _text("tools/ci/config_quality.py")
    assert "uv run --frozen --offline python -m nox -s config_quality" in _text(
        ".pre-commit-config.yaml"
    )


def test_python_test_gate_uses_portable_runtime_paths_and_lock(tmp_path: Path) -> None:
    gate = PythonTestGate(
        Settings("0" * 40, tmp_path / "evidence", tmp_path / "pytest", None, None, 1, None, 1, None)
    )
    source = _text("tools/ci/python_test_gate.py")
    assert Path(sys.executable) == PYTHON
    assert gate.identity_home.parent == Path(tempfile.gettempdir())
    assert "FileLock" in source
    assert '"GIT_CONFIG_GLOBAL": os.devnull' in source
    assert 'ROOT / ".venv/bin/python"' not in source
