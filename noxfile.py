"""Repository-owned sessions executed inside the single uv-locked `.venv`."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from importlib import import_module
from pathlib import Path
from typing import cast

import nox
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
PythonTestGate = import_module("tools.ci.python_test_gate").PythonTestGate
run_dependency_hygiene = import_module("tools.ci.dependency_hygiene").run
run_architecture_projection = import_module("tools.ci.architecture_projection").main
run_ci_templates = import_module("tools.ci.ci_templates").check_templates
run_config_quality = import_module("tools.ci.config_quality").run
format_config_quality = import_module("tools.ci.config_quality").format_configs
run_format_selection = import_module("tools.ci.format_selection").main
run_hosted_observation = import_module("tools.ci.hosted_observation").capture_observation
run_install_smoke = import_module("tools.ci.local_install_smoke").run
prepare_install_supply_owner = import_module("tools.ci.local_install_smoke").prepare_supply
run_local_ci = import_module("tools.ci.local_ci").run
run_python_vulnerability_audit = import_module("tools.ci.python_vulnerability_audit").run
run_repository_hygiene = import_module("tools.ci.repository_hygiene").audit
run_release_supply_chain = import_module("tools.ci.release_supply_chain").run
run_runbook_registry = import_module("tools.ci.runbook_registry").main
RUFF_CACHE = ROOT / "build/runtime/tool-cache/ruff"
PROJECT_SCRIPTS = Path(sys.executable).parent
PROSE_CONFIG = ROOT / ".config/checks/prose/codespell.toml"
NODEJS_WHEEL = Path(import_module("nodejs_wheel").__file__).resolve().parent
NODE = NODEJS_WHEEL / "bin" / ("node.exe" if os.name == "nt" else "node")
MARKDOWNLINT = ROOT / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"
PRETTIER = ROOT / "node_modules/prettier/bin/prettier.cjs"
SVGO = ROOT / "node_modules/svgo/bin/svgo.js"

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


@nox.session(python=False, name="format")
def format_repository(session: nox.Session) -> None:
    """Canonicalize selected mutable carriers before read-only validation."""
    operations = {
        "python": _format_python,
        "config": _format_config,
        "markdown": _format_markdown,
        "shell": _format_shell,
        "javascript": _format_javascript,
        "svg": _format_svg,
        "hygiene": _format_hygiene,
    }
    selected = frozenset(session.posargs or operations)
    unknown = selected - operations.keys()
    if unknown:
        session.error("unknown format carrier: " + ", ".join(sorted(unknown)))
    for name, operation in operations.items():
        if name in selected:
            operation(session)


def _format_python(session: nox.Session) -> None:
    paths = _candidate_python_paths(session)
    common = ("--cache-dir", str(RUFF_CACHE), "--config", "ruff.toml")
    session.run(_project_script("ruff"), "format", *common, *paths)


def _format_config(_session: nox.Session) -> None:
    format_config_quality((), node=NODE, prettier=PRETTIER)


def _format_markdown(session: nox.Session) -> None:
    paths = tuple(
        f":{path}"
        for path in _tracked_paths("*.md")
        if not path.startswith(("evidence/", "openspec/"))
    )
    if not paths:
        return
    session.run(
        str(NODE),
        str(MARKDOWNLINT),
        "--fix",
        "--config",
        ".config/checks/markdown/.markdownlint-cli2.yaml",
        "--no-globs",
        *paths,
    )


def _format_shell(session: nox.Session) -> None:
    paths = _tracked_paths("*.sh", "*.bash", "*.zsh")
    if paths:
        session.run(_project_script("shfmt"), "-w", "-i", "2", "-ci", "-bn", *paths)


def _format_javascript(session: nox.Session) -> None:
    paths = _tracked_paths("*.js", "*.mjs", "*.cjs")
    if paths:
        session.run(
            str(NODE), str(PRETTIER), "--write", "--no-config", "--print-width", "100", *paths
        )


def _format_svg(session: nox.Session) -> None:
    paths = _tracked_paths("*.svg")
    if paths:
        session.run(
            str(NODE),
            str(SVGO),
            "--multipass",
            "--pretty",
            "--indent",
            "2",
            "--eol",
            "lf",
            "--final-newline",
            *paths,
        )


def _format_hygiene(_session: nox.Session) -> None:
    selected = (*_tracked_paths("*.ini", "*.cfg"), "LICENSE")
    for relative in selected:
        path = ROOT / relative
        lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
        path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


@nox.session(python=False)
def lint(session: nox.Session) -> None:
    """Run repository-wide Ruff lint and formatting checks without mutation."""
    paths = _candidate_python_paths(session)
    RUFF_CACHE.mkdir(parents=True, exist_ok=True)
    common = ("--cache-dir", str(RUFF_CACHE), "--config", "ruff.toml")
    ruff = _project_script("ruff")
    session.run(ruff, "check", "--ignore-noqa", *common, *paths)
    session.run(ruff, "format", *common, "--check", *paths)


def _tracked_paths(*patterns: str) -> tuple[str, ...]:
    output = subprocess.check_output(("git", "ls-files", "-z", *patterns), cwd=ROOT)
    return tuple(item.decode() for item in output.split(b"\0") if item)


@nox.session(python=False)
def javascript_lint(session: nox.Session) -> None:
    """Check JavaScript distribution carriers with repository-locked Prettier."""
    paths = _tracked_paths("*.js", "*.mjs", "*.cjs")
    if paths:
        session.run(
            str(NODE), str(PRETTIER), "--check", "--no-config", "--print-width", "100", *paths
        )


@nox.session(python=False)
def svg_lint(session: nox.Session) -> None:
    """Require SVG sources to equal the repository-locked SVGO canonical form."""
    for relative in _tracked_paths("*.svg"):
        completed = subprocess.run(
            (
                str(NODE),
                str(SVGO),
                "--multipass",
                "--pretty",
                "--indent",
                "2",
                "--eol",
                "lf",
                "--final-newline",
                "--input",
                relative,
                "--output",
                "-",
            ),
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        if completed.stdout != (ROOT / relative).read_bytes():
            session.error(f"{relative}: SVG format drift")


@nox.session(python=False)
def asset_validation(session: nox.Session) -> None:
    """Validate tracked raster assets without inventing a lossy formatter."""
    for relative in _tracked_paths("*.png"):
        with Image.open(ROOT / relative) as image:
            image.verify()
        session.log(f"{relative}: valid PNG")


@nox.session(python=False)
def format_check(session: nox.Session) -> None:
    """Run the all-carrier read-only format and validation closure."""
    lint(session)
    config_quality(session)
    markdown_lint(session)
    shell_lint(session)
    javascript_lint(session)
    svg_lint(session)
    asset_validation(session)


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
        env={
            "ETHOS_BUILD_NODE": str(NODE),
            "ETHOS_BUILD_NPM_CLI": str(NODEJS_WHEEL / "lib/node_modules/npm/bin/npm-cli.js"),
        },
    )


@nox.session(python=False)
def build(session: nox.Session) -> None:
    """Build the Hatchling wheel through the locked uv project environment."""
    _build_wheel(session)


@nox.session(python=False)
def prepare_install_supply(_session: nox.Session) -> None:
    """Prepare the lock-bound dependency supply consumed by offline install proof."""
    prepare_install_supply_owner()


@nox.session(python=False)
def install_smoke(session: nox.Session) -> None:
    """Prove offline installation from the single built wheel."""
    run_install_smoke(session)


@nox.session(python=False)
def host_conformance(session: nox.Session) -> None:
    """Execute the installed-wheel contract on the current real host."""
    _build_wheel(session)
    prepare_install_supply(session)
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
def prose(session: nox.Session) -> None:
    """Check current human-facing text with the locked spelling owner."""
    config = tomllib.loads(PROSE_CONFIG.read_text(encoding="utf-8"))
    paths = tuple(str(ROOT / path) for path in config["paths"])
    session.run(
        _project_script("codespell"),
        "--toml",
        str(PROSE_CONFIG),
        "--count",
        "--quiet-level=2",
        *paths,
    )


@nox.session(python=False)
def shell_lint(session: nox.Session) -> None:
    """Check every tracked shell carrier with locked cross-platform ShellCheck."""
    output = cast(
        "str",
        session.run("git", "ls-files", "-z", "*.sh", silent=True),
    )
    paths = tuple(path for path in output.split("\0") if path and (ROOT / path).is_file())
    if paths:
        session.run(
            _project_script("shellcheck"),
            "--rcfile=.config/checks/shell/.shellcheckrc",
            *paths,
        )


@nox.session(python=False)
def markdown_lint(session: nox.Session) -> None:
    """Check Markdown with the exact repository-locked Node dependency."""
    executable = ROOT / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"
    if not NODE.is_file() or not executable.is_file():
        session.error("locked markdownlint-cli2 is missing; run npm ci --ignore-scripts")
    session.run(
        str(NODE),
        str(executable),
        "--config",
        ".config/checks/markdown/.markdownlint-cli2.yaml",
    )


@nox.session(python=False)
def config_quality(session: nox.Session) -> None:
    """Check TOML, YAML, JSON, and hook configuration without shell orchestration."""
    paths = tuple(session.posargs)
    failures = run_config_quality(paths, node=NODE)
    if failures:
        session.error("configuration quality failed:\n" + "\n".join(failures))
    if not paths or Path(".pre-commit-config.yaml") in map(Path, paths):
        session.run(_project_script("pre-commit"), "validate-config", ".pre-commit-config.yaml")


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
