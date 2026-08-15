"""Quality-gate implementations consumed by the typed registry."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from importlib import import_module
from pathlib import Path
from typing import cast

from PIL import Image

from tools.ci.delivery.pipeline import DeliveryPipeline
from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ProjectRuntime.discover(ROOT)

DELIVERY = DeliveryPipeline.from_runtime(RUNTIME)
NODE = DELIVERY.node
MARKDOWNLINT = ROOT / "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs"
PRETTIER = ROOT / "node_modules/prettier/bin/prettier.cjs"
SVGO = ROOT / "node_modules/svgo/bin/svgo.js"
RUFF_CACHE = ROOT / "build/runtime/tool-cache/ruff"
PythonTestGate = import_module("tools.ci.python_test_gate").PythonTestGate
PUBLIC_SESSIONS = (
    "lint",
    "format_check",
    "tests",
    "coverage_floor",
    "build",
    "prepare_install_supply",
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
    return tuple(item.decode() for item in output.split(b"\0") if item)


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
    paths = tuple(path for path in output.split("\0") if path)
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


def format_check(session) -> None:
    lint(session)
    config_quality(session)
    markdown_lint(session)
    shell_lint(session)
    javascript_lint(session)
    svg_lint(session)
    asset_validation(session)


def lint(session) -> None:
    paths = _python_paths(session)
    RUFF_CACHE.mkdir(parents=True, exist_ok=True)
    common = ("--cache-dir", str(RUFF_CACHE), "--config", "ruff.toml")
    executable = RUNTIME.script("ruff")
    session.run(executable, "check", "--ignore-noqa", *common, *paths)
    session.run(executable, "format", *common, "--check", *paths)


def tests(session) -> None:
    PythonTestGate.from_environment().run_tests(session)


def coverage_floor(session) -> None:
    PythonTestGate.from_environment().enforce_floor(session)


def build(session) -> None:
    DELIVERY.build(session)


def prepare_install_supply(_session) -> None:
    DELIVERY.prepare_supply()


def install_smoke(session) -> None:
    DELIVERY.prove_install(session)


def host_conformance(session) -> None:
    DELIVERY.prove_host(session)


def dependencies(session) -> None:
    import_module("tools.ci.dependency_hygiene").run(session)


def vulnerabilities(session) -> None:
    import_module("tools.ci.python_vulnerability_audit").run(session)


def supply_chain(session) -> None:
    import_module("tools.ci.release_supply_chain").run(session)


def ci_templates(session) -> None:
    if import_module("tools.ci.ci_templates").check_templates(json_output=True):
        session.error("CI provider projections differ from their owners")


def architecture_projection(session) -> None:
    if import_module("tools.ci.architecture_projection").main():
        session.error("architecture projections differ from their owner")


def format_selection(session) -> None:
    if import_module("tools.ci.format_selection").main():
        session.error("format selection policy did not pass")


def repository_hygiene(session) -> None:
    failures = import_module("tools.ci.repository_hygiene").audit(ROOT)
    if failures:
        session.error("repository hygiene failed:\n" + "\n".join(failures))


def prose(session) -> None:
    policy = ROOT / ".config/checks/prose/codespell.toml"
    declared = tomllib.loads(policy.read_text(encoding="utf-8")).get("paths", [])
    paths = tuple(str(path) for path in declared if isinstance(path, str) and path)
    if not paths:
        session.error("prose policy paths are missing")
    session.run(
        RUNTIME.script("codespell"),
        "--toml",
        str(policy),
        "--count",
        "--quiet-level=2",
        *paths,
    )


def shell_lint(session) -> None:
    paths = _paths("*.sh")
    if paths:
        session.run(
            RUNTIME.script("shellcheck"), "--rcfile=.config/checks/shell/.shellcheckrc", *paths
        )


def markdown_lint(session) -> None:
    if not NODE.is_file() or not MARKDOWNLINT.is_file():
        session.error("locked markdownlint-cli2 is missing; run npm ci --ignore-scripts")
    session.run(
        str(NODE), str(MARKDOWNLINT), "--config", ".config/checks/markdown/.markdownlint-cli2.yaml"
    )


def config_quality(session) -> None:
    failures = import_module("tools.ci.config_quality").run(tuple(session.posargs), node=NODE)
    if failures:
        session.error("configuration quality failed:\n" + "\n".join(failures))
    if not session.posargs or ".pre-commit-config.yaml" in session.posargs:
        session.run(RUNTIME.script("pre-commit"), "validate-config", ".pre-commit-config.yaml")


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
        ".config/checks/import-linter/contracts.ini",
        env={"PYTHONPATH": str(ROOT / "src")},
    )


def schemas(session) -> None:
    session.run(
        sys.executable,
        "-m",
        "check_jsonschema",
        "--check-metaschema",
        *sorted(str(path) for path in ROOT.glob("system/schemas/**/*.json")),
        "-o",
        "json",
    )


def local_ci(session) -> None:
    import_module("tools.ci.local_ci").run(session)


def javascript_lint(session) -> None:
    paths = _paths("*.js", "*.mjs", "*.cjs")
    if paths:
        session.run(
            str(NODE), str(PRETTIER), "--check", "--no-config", "--print-width", "100", *paths
        )


def svg_lint(session) -> None:
    for relative in _paths("*.svg"):
        result = subprocess.run(
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
        if result.stdout != (ROOT / relative).read_bytes():
            session.error(f"{relative}: SVG format drift")


def asset_validation(session) -> None:
    for relative in _paths("*.png"):
        with Image.open(ROOT / relative) as image:
            image.verify()
        session.log(f"{relative}: valid PNG")
