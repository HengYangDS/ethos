"""Repository-owned sessions executed inside the single uv-locked `.venv`."""

from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
from typing import cast

import nox

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
PythonTestGate = import_module("tools.ci.python_test_gate").PythonTestGate
run_dependency_hygiene = import_module("tools.ci.dependency_hygiene").run
run_architecture_projection = import_module("tools.ci.architecture_projection").main
run_ci_templates = import_module("tools.ci.ci_templates").check_templates
run_format_selection = import_module("tools.ci.format_selection").main
run_hosted_observation = import_module("tools.ci.hosted_observation").capture_observation
run_install_smoke = import_module("tools.ci.local_install_smoke").run
run_local_ci = import_module("tools.ci.local_ci").run
run_python_vulnerability_audit = import_module("tools.ci.python_vulnerability_audit").run
run_repository_hygiene = import_module("tools.ci.repository_hygiene").audit
run_release_supply_chain = import_module("tools.ci.release_supply_chain").run
run_runbook_registry = import_module("tools.ci.runbook_registry").main
RUFF_CACHE = ROOT / "build/runtime/tool-cache/ruff"
PROJECT_SCRIPTS = Path(sys.executable).parent

nox.options.default_venv_backend = "none"
nox.options.error_on_external_run = True
nox.options.sessions = ["lint"]


def _candidate_python_paths(session: nox.Session) -> tuple[str, ...]:
    output = cast(
        "str",
        session.run(
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "*.py",
            "*.pyi",
            silent=True,
        ),
    )
    paths = tuple(path for path in output.split("\0") if path)
    if not paths:
        msg = "no candidate Python files found for Ruff"
        raise RuntimeError(msg)
    return paths


def _project_script(name: str) -> str:
    """Resolve a console script from the active project environment only."""
    suffix = ".exe" if os.name == "nt" else ""
    return str(PROJECT_SCRIPTS / f"{name}{suffix}")


@nox.session(python=False)
def lint(session: nox.Session) -> None:
    """Run repository-wide Ruff lint and formatting without suppressions."""
    paths = _candidate_python_paths(session)
    RUFF_CACHE.mkdir(parents=True, exist_ok=True)
    common = ("--cache-dir", str(RUFF_CACHE), "--config", "ruff.toml")
    ruff = _project_script("ruff")
    session.run(ruff, "check", "--ignore-noqa", *common, *paths)
    session.run(ruff, "format", *common, "--check", *paths)


@nox.session(python=False)
def tests(session: nox.Session) -> None:
    """Run the isolated unit and architecture graph with branch coverage."""
    PythonTestGate.from_environment().run_tests(session)


@nox.session(python=False)
def coverage_floor(session: nox.Session) -> None:
    """Enforce the hard floor against current-HEAD coverage evidence."""
    PythonTestGate.from_environment().enforce_floor(session)


def _build_wheel(session: nox.Session) -> None:
    session.run(
        _project_script("uv"),
        "build",
        "--offline",
        "--wheel",
        "--out-dir",
        "build/artifacts/python",
        "--clear",
        "--no-create-gitignore",
    )


@nox.session(python=False)
def build(session: nox.Session) -> None:
    """Build the Hatchling wheel through the locked uv project environment."""
    _build_wheel(session)


@nox.session(python=False)
def install_smoke(session: nox.Session) -> None:
    """Prove offline installation from the single built wheel."""
    run_install_smoke(session)


@nox.session(python=False)
def host_conformance(session: nox.Session) -> None:
    """Execute the installed-wheel contract on the current real host."""
    _build_wheel(session)
    run_install_smoke(session)
    session.run(
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/architecture/test_portable_toolchain.py",
        "tests/architecture/test_local_install_smoke.py",
    )


@nox.session(python=False)
def dependencies(session: nox.Session) -> None:
    """Validate direct Python dependency declarations with deptry."""
    run_dependency_hygiene(session)


@nox.session(python=False)
def vulnerabilities(session: nox.Session) -> None:
    """Audit the frozen Python lock with uv's native OSV client."""
    run_python_vulnerability_audit(session)


@nox.session(python=False)
def supply_chain(session: nox.Session) -> None:
    """Generate the exact-wheel SPDX SBOM and bounded receipt."""
    run_release_supply_chain(session)


@nox.session(python=False)
def ci_templates(session: nox.Session) -> None:
    """Verify that provider CI files equal their canonical templates."""
    if run_ci_templates(json_output=True):
        session.error("CI provider projections differ from their owners")


@nox.session(python=False)
def architecture_projection(session: nox.Session) -> None:
    """Verify generated architecture views against their source model."""
    if run_architecture_projection():
        session.error("architecture projections differ from their owner")


@nox.session(python=False)
def format_selection(session: nox.Session) -> None:
    """Verify every tracked extension and executable carrier is governed."""
    if run_format_selection():
        session.error("format selection policy did not pass")


@nox.session(python=False)
def repository_hygiene(session: nox.Session) -> None:
    """Enforce cross-platform repository shape and zero suppressions."""
    failures = run_repository_hygiene(ROOT)
    if failures:
        session.error("repository hygiene failed:\n" + "\n".join(failures))


@nox.session(python=False)
def runbook_registry(session: nox.Session) -> None:
    """Verify the runbook projection against its declared commands."""
    if run_runbook_registry():
        session.error("runbook registry did not pass")


@nox.session(python=False)
def hosted_observation(session: nox.Session) -> None:
    """Capture bounded hosted-provider observations without minting proof."""
    execute = os.environ.get("ETHOS_HOSTED_OBSERVATION_EXECUTE") == "1"
    result = run_hosted_observation(execute=execute)
    if execute and result:
        session.error("hosted provider observation failed")


@nox.session(python=False)
def docstrings(session: nox.Session) -> None:
    """Run the docstring contract through the repository CLI."""
    session.run(
        sys.executable,
        "-m",
        "ethos.cli",
        "prove",
        "--execute",
        "--gate",
        "docstrings",
        "--json",
    )


@nox.session(python=False)
def module_layout(session: nox.Session) -> None:
    """Run the semantic module-layout contract through the repository CLI."""
    session.run(
        sys.executable,
        "-m",
        "ethos.cli",
        "prove",
        "--execute",
        "--gate",
        "module-layout",
        "--json",
    )


@nox.session(python=False)
def product_boundary(session: nox.Session) -> None:
    """Run product-boundary admission through the repository CLI."""
    session.run(
        sys.executable,
        "-m",
        "ethos.cli",
        "prove",
        "--execute",
        "--gate",
        "product-boundary",
        "--json",
    )


@nox.session(python=False)
def import_boundaries(session: nox.Session) -> None:
    """Run import-linter against the repository's declared contracts."""
    cache = ROOT / "build/runtime/tool-cache/import-linter"
    cache.mkdir(parents=True, exist_ok=True)
    pythonpath = str(ROOT / "src")
    if inherited := os.environ.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}{os.pathsep}{inherited}"
    session.run(
        _project_script("lint-imports"),
        "--cache-dir",
        str(cache),
        "--config",
        ".config/checks/import-linter/contracts.ini",
        env={"PYTHONPATH": pythonpath},
    )


@nox.session(python=False)
def schemas(session: nox.Session) -> None:
    """Validate repository JSON Schemas against their metaschema."""
    session.run(
        sys.executable,
        "-m",
        "check_jsonschema",
        "--check-metaschema",
        *sorted(str(path) for path in ROOT.glob("system/schemas/**/*.json")),
        "-o",
        "json",
    )


@nox.session(python=False)
def local_ci(session: nox.Session) -> None:
    """Run the cross-platform local verification and delivery closure."""
    run_local_ci(session)
