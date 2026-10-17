"""Quality-gate implementations consumed by the typed registry."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ProjectRuntime.discover(ROOT)
RUFF_CACHE = ROOT / "build/runtime/tool-cache/ruff"
PRE_COMMIT_CONFIG = ".config/checks/pre-commit/.pre-commit-config.yaml"
PUBLIC_SESSIONS = (
    "lint",
    "format",
    "format_check",
    "tests",
    "coverage_floor",
    "build",
    "install_smoke",
    "host_conformance",
    "dependencies",
    "vulnerabilities",
    "supply_chain",
    "ci_templates",
    "architecture_projection",
    "format_selection",
    "repository_hygiene",
    "prose",
    "shell_lint",
    "markdown_lint",
    "javascript_lint",
    "javascript_tests",
    "svg_lint",
    "asset_validation",
    "config_quality",
    "hosted_observation",
    "docstrings",
    "module_layout",
    "product_boundary",
    "import_boundaries",
    "schemas",
    "local_ci",
)


def _paths(*patterns: str) -> tuple[str, ...]:
    output = subprocess.check_output(("git", "ls-files", "-z", *patterns), cwd=ROOT)
    paths = tuple(item.decode() for item in output.split(b"\0") if item)
    return tuple(path for path in paths if (ROOT / path).is_file())


def _python_paths(session) -> tuple[str, ...]:
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
    paths = tuple(path for path in output.split("\0") if path and (ROOT / path).is_file())
    if not paths:
        message = "no candidate Python files found for Ruff"
        raise RuntimeError(message)
    return paths


def _host(session, name: str) -> None:
    head = cast("str", session.run("git", "rev-parse", "HEAD", silent=True)).strip()
    session.run(
        sys.executable,
        "-m",
        "ethos.cli",
        "prove",
        "--host",
        "--execute",
        "--gate",
        name,
        "--expect-head",
        head,
        "--json",
    )


def source_format(session) -> None:
    """Project native preview or explicitly authorized fixing without owning format policy."""
    _source_format(session, checking=False)


def format_check(session) -> None:
    """Check the exact same selected native postimages without source writes."""
    _source_format(session, checking=True)


def _source_format(session, *, checking: bool) -> None:
    session.run(
        str(RUNTIME.python),
        "-B",
        "-m",
        "ethos.cli",
        "lane",
        "format",
        "--root",
        str(ROOT),
        *(("--check",) if checking else ()),
        *session.posargs,
        "--json",
    )


SESSION_IMPLEMENTATIONS = {"format": source_format}


def lint(session) -> None:
    paths = _python_paths(session)
    RUFF_CACHE.mkdir(parents=True, exist_ok=True)
    common = ("--cache-dir", str(RUFF_CACHE), "--config", ".config/checks/ruff/ruff.toml")
    executable = RUNTIME.script("ruff")
    session.run(executable, "check", "--ignore-noqa", *common, *paths)
    session.run(executable, "format", *common, "--check", *paths)


def tests(session) -> None:
    gate = import_module("tools.ci.python_test_gate").PythonTestGate.from_environment(
        node_package_supply=RUNTIME.node_package_supply()
    )
    gate.compile_bytecode()
    try:
        gate.run_tests(session)
    except Exception:
        try:
            gate.render_report()
        except (OSError, RuntimeError, ValueError) as error:
            session.log(f"Allure report unavailable after failed tests: {error}")
        raise
    gate.render_report()


def coverage_floor(session) -> None:
    gate = import_module("tools.ci.python_test_gate").PythonTestGate.from_environment(
        node_package_supply=RUNTIME.node_package_supply()
    )
    gate.enforce_floor(session)


def build(session) -> None:
    owner = import_module("tools.ci.delivery.pipeline")
    head = owner.release_build_head(tuple(session.posargs))
    if head:
        import_module("tools.ci.dependency_audit").run(
            session, root=RUNTIME.root, scope="production-release"
        )
    owner.DeliveryPipeline.from_runtime(RUNTIME).build(session, release_head=head)


def install_smoke(session) -> None:
    owner = import_module("tools.ci.delivery.pipeline")
    head = owner.release_build_head(tuple(session.posargs))
    if head:
        import_module("tools.ci.dependency_audit").run(
            session, root=RUNTIME.root, scope="production-release"
        )
    owner.DeliveryPipeline.from_runtime(RUNTIME).prove_install(session, release_head=head)


def host_conformance(session) -> None:
    import_module("tools.ci.delivery.pipeline").DeliveryPipeline.from_runtime(RUNTIME).prove_host(
        session
    )


def dependencies(session) -> None:
    import_module("tools.ci.dependency_hygiene").run(session)


def vulnerabilities(session) -> None:
    owner = import_module("tools.ci.dependency_audit")
    owner.run(session, root=RUNTIME.root, scope=owner.requested_scope(tuple(session.posargs)))


def supply_chain(session) -> None:
    import_module("tools.ci.release_supply_chain").run(session)


def ci_templates(session) -> None:
    if import_module("tools.ci.ci_templates").check_templates(json_output=True):
        session.error("CI provider projections differ from their owners")


def architecture_projection(session) -> None:
    if import_module("tools.ci.architecture_projection").main():
        session.error("architecture projections differ from their owner")
    with TemporaryDirectory(prefix="ethos-projection-check-") as temporary:
        session.run(
            str(RUNTIME.python),
            "-m",
            "pytest",
            "-c",
            ".config/checks/pytest/pytest.toml",
            "--rootdir=.",
            "tests/unit/projection",
            "-q",
            "-o",
            "addopts=",
            "--no-cov",
            f"--basetemp={Path(temporary).resolve()}",
        )


def format_selection(session) -> None:
    if import_module("tools.ci.format_selection").main():
        session.error("format selection policy did not pass")


def repository_hygiene(session) -> None:
    failures = import_module("tools.ci.repository_hygiene").audit(ROOT)
    if failures:
        session.error("repository hygiene failed:\n" + "\n".join(failures))


def prose(session) -> None:
    report = import_module("ethos.adapters.gates.tool").prose_report(ROOT)
    session.log(json.dumps(report))
    if report["verdict"] != "pass":
        session.error("native spelling did not pass")


def shell_lint(session) -> None:
    paths = _paths("*.sh")
    if paths:
        session.run(
            RUNTIME.script("shellcheck"), "--rcfile=.config/checks/shellcheck/.shellcheckrc", *paths
        )
        session.run(RUNTIME.script("shfmt"), "-d", *paths)


def markdown_lint(session) -> None:
    report = import_module("ethos.adapters.gates.tool").markdown_lint_report(ROOT)
    session.log(json.dumps(report))
    if report["verdict"] != "pass":
        session.error("native Markdown format and semantic lint did not pass")


def config_quality(session) -> None:
    report = import_module("ethos.adapters.gates.configuration").configuration_report(
        ROOT, paths=tuple(session.posargs)
    )
    session.log(json.dumps(report))
    if report["verdict"] != "pass":
        session.error("configuration quality failed: " + str(report["required_gaps"]))
    if not session.posargs or PRE_COMMIT_CONFIG in session.posargs:
        session.run(RUNTIME.script("pre-commit"), "validate-config", PRE_COMMIT_CONFIG)


def hosted_observation(session) -> None:
    execute = os.environ.get("ETHOS_HOSTED_OBSERVATION_EXECUTE") == "1"
    result = import_module("tools.ci.hosted_observation").capture_observation(execute=execute)
    if execute and result:
        session.error("hosted provider observation failed")


def docstrings(session) -> None:
    _host(session, "docstrings")


def module_layout(session) -> None:
    _host(session, "module-layout")


def product_boundary(session) -> None:
    _host(session, "product-boundary")


def import_boundaries(session) -> None:
    cache = ROOT / "build/runtime/tool-cache/import-linter"
    cache.mkdir(parents=True, exist_ok=True)
    session.run(
        RUNTIME.script("lint-imports"),
        "--cache-dir",
        str(cache),
        "--config",
        ".config/checks/import-linter/import-linter.toml",
        env={"PYTHONPATH": str(ROOT / "src")},
    )


def schemas(session) -> None:
    report = import_module("ethos.repository.policy.schema").schema_validation_report(ROOT)
    session.log(json.dumps(report, sort_keys=True))
    if report["verdict"] != "pass":
        session.error("schema validation failed: " + ", ".join(report["required_gaps"]))


def local_ci(session) -> None:
    import_module("tools.ci.local_ci").run(session)


def javascript_tests(session) -> None:
    """Execute package-owned behavior with locked tools and disposable npm state."""
    command = RUNTIME.npm_command()
    with TemporaryDirectory(prefix="ethos-javascript-tests-") as cache:
        session.run(
            *command,
            "run",
            "test:npm",
            env={
                "PATH": os.pathsep.join((str(Path(command[0]).parent), os.environ.get("PATH", ""))),
                "npm_config_cache": cache,
                "npm_config_offline": "true",
                "npm_config_update_notifier": "false",
                "npm_config_audit": "false",
                "npm_config_fund": "false",
            },
        )


def javascript_lint(session) -> None:
    paths = _paths("*.js", "*.mjs", "*.cjs")
    if paths:
        _, subjects = import_module("ethos.adapters.repo.gate_policy").observe_quality_subjects(
            ROOT, language="javascript"
        )
        paths = tuple(subject.path for subject in subjects if subject.requires_authored_analysis)
        if not paths:
            return
        analyzer = import_module("ethos.adapters.gates.javascript.analysis")
        observation = analyzer.static_observation(ROOT, paths)
        if observation["verdict"] != "pass":
            session.error(json.dumps(observation))
        _check_source_paths(session, paths)


def svg_lint(session) -> None:
    paths = _paths("*.svg")
    if paths:
        _check_source_paths(session, paths)


def _check_source_paths(session, paths: tuple[str, ...]) -> None:
    report = import_module("ethos.adapters.gates.formatting").source_format_report(
        ROOT, paths=paths
    )
    session.log(json.dumps(report))
    if report["verdict"] != "pass":
        session.error("native source formatting did not pass")


def asset_validation(session) -> None:
    for relative in _paths("*.png"):
        with import_module("PIL.Image").open(ROOT / relative) as image:
            image.verify()
        session.log(f"{relative}: valid PNG")
