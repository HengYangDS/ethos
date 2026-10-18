"""Native Nox producer fixtures for exact selected-wheel quality attempts."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.contracts.gates import Gate
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from tests.unit.adoption.quality.native.conftest import NativeNoxSupply


def native_quality_gate(root: Path, supply: NativeNoxSupply, outcome: str = "pass") -> Gate:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    behavior, static = f"behavior-{version}", f"static-{version}"
    source = f'''"""A native producer for one exact quality attempt."""
import json
import hashlib
import os
from pathlib import Path
import nox

VERSION = {version!r}
UV = {str(supply.uv)!r}
FLOOR = {str(supply.project)!r}
OUTCOME = {outcome!r}
nox.options.envdir = {str(supply.environments)!r}
nox.options.reuse_existing_virtualenvs = True

def prepare(session):
    requirement = os.environ["ETHOS_NATIVE_OBSERVER_REQUIREMENT"]
    from urllib.parse import urlsplit
    from urllib.request import url2pathname
    parsed = urlsplit(requirement.removeprefix("ethos @ "))
    wheel = Path(url2pathname(parsed.path))
    with wheel.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == parsed.fragment[7:]
    python = Path(session.virtualenv.location) / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python")
    session.run(UV, "sync", "--offline", "--frozen", "--no-default-groups", "--group", "dev",
        "--no-install-project", "--inexact", "--no-python-downloads", "--project", FLOOR,
        "--python", str(python), env={{"UV_PROJECT_ENVIRONMENT": str(session.virtualenv.location)}},
        external=True)
    session.run(UV, "pip", "install", "--offline", "--no-deps", "--python", str(python),
        requirement, external=True)
    return python

def runtime(session, python):
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    session.run(str(python), "-B", "-I", "-c",
        "import json,sys; from pathlib import Path; "
        "from ethos.domain.quality.observer import runtime_identity; "
        "Path(sys.argv[1]).write_text(json.dumps(runtime_identity()))",
        str(output / (session.name + "-runtime.json")), external=True)
    return output

@nox.session(python=VERSION, venv_backend="uv")
def behavior(session):
    python = prepare(session)
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    if OUTCOME == "runtime-detached":
        runtime(session, python)
    with (output / "behavior-count.txt").open("a") as stream:
        stream.write("one\\n")
    env = {{"COVERAGE_FILE": str(output / ".coverage")}}
    config = (".config/pytest-alternate/pytest.toml" if OUTCOME == "runtime-config"
              else ".config/pytest/pytest.toml")
    capture = [] if OUTCOME == "runtime-detached" else [
        "-p", "ethos.surface.pytest.plugin",
        "--ethos-runtime-output=" + str(output / (session.name + "-runtime.json")),
        "--ethos-native-session=" + session.name + "-" + VERSION,
    ]
    session.run(str(python), "-B", "-I", "-m", "pytest", "--rootdir", ".", "-c", config,
        *capture, "-q", "-W", "error",
        "--junitxml=" + str(output / "behavior.xml"),
        "--report-log=" + str(output / "behavior-events.jsonl"), "--cov=src",
        "--cov-branch", "--cov-report=xml:" + str(output / "coverage.xml"),
        "tests", env=env, external=True)

@nox.session(python=VERSION, venv_backend="uv")
def static(session):
    python = prepare(session)
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    targets = ("src/app.py",) if OUTCOME == "static-scope" else ("src", "tests", "noxfile.py")
    config = ".config/ruff-alternate.toml" if OUTCOME == "static-config" else ".config/ruff.toml"
    if OUTCOME == "static-detached":
        runtime(session, python)
        session.run(str(python), "-m", "ruff", "check", "--config", config,
            "--output-format", "sarif", "--output-file", str(output / "ruff.sarif"),
            "src", "tests", "noxfile.py", external=True)
    else:
        binary = python.with_name("ruff.exe" if os.name == "nt" else "ruff")
        session.run(str(python), "-B", "-I", "-m", "ethos.domain.quality.nox", "run",
            "--runtime-output", str(output / (session.name + "-runtime.json")),
            "--session", session.name + "-" + VERSION, "--configuration", config, "--",
            str(binary), "check", "--config", config, "--verbose", "--no-cache",
            "--output-format", "sarif", "--output-file", str(output / "ruff.sarif"),
            *targets, external=True)
    if OUTCOME == "timeout":
        session.run(str(python), "-c",
            "import time; print('timeout-sentinel', flush=True); time.sleep(60)",
            external=True)
    if OUTCOME == "missing":
        (output / "coverage.xml").unlink()
    if OUTCOME == "junit":
        from xml.etree import ElementTree
        target = output / "behavior.xml"
        tree = ElementTree.fromstring(target.read_bytes())
        ElementTree.SubElement(next(tree.iter("testcase")), "failure")
        target.write_bytes(ElementTree.tostring(tree))
    if OUTCOME == "runtime":
        target = output / (session.name + "-runtime.json")
        value = json.loads(target.read_text())
        value["version"] = [0, 0, 0]
        target.write_text(json.dumps(value))
    if OUTCOME == "runtime-path":
        target = output / (session.name + "-runtime.json")
        value = json.loads(target.read_text())
        value["executable"] = str(output / "missing-interpreter")
        value["prefix"] = str(output / "missing-environment")
        target.write_text(json.dumps(value))
    if OUTCOME == "unsafe-output":
        (output / "coverage.xml").unlink()
        (output / "coverage.xml").mkdir()
    if OUTCOME == "dirty-source":
        with Path("pyproject.toml").open("a") as stream:
            stream.write("\\n")
    if OUTCOME in {{"advance-head", "commit-change"}}:
        if OUTCOME == "commit-change":
            with Path("src/app.py").open("a") as stream:
                stream.write("\\nextra = 43\\n")
        session.run("git", "add", "--all", external=True)
        session.run("git", "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m",
            "observe: move source during the attempt", external=True)
'''
    fixture = Path(__file__).resolve().parents[1] / "fixtures/quality-sample"
    metadata = (fixture / "pyproject.toml").read_text()
    lock = (fixture / "uv.lock").read_text()
    if outcome == "toolchain":
        selected = next(
            item["version"] for item in tomllib.loads(lock)["package"] if item["name"] == "ruff"
        )
        lock = lock.replace(
            f'name = "ruff"\nversion = "{selected}"',
            'name = "ruff"\nversion = "0.0.1"',
        )
        assert 'name = "ruff"\nversion = "0.0.1"' in lock
    repo = committed_source_repo(
        root,
        {
            ".gitignore": ".nox/\n.pytest_cache/\n__pycache__/\n",
            ".gitattributes": "noxfile.py ethos-role=tooling\n",
            "noxfile.py": source,
            ".config/pytest/pytest.toml": (
                '[pytest]\npythonpath = ["../.."]\nfilterwarnings = ["error"]\n'
            ),
            ".config/pytest-alternate/pytest.toml": (
                '[pytest]\npythonpath = ["../.."]\nfilterwarnings = ["error"]\n'
            ),
            ".config/ruff.toml": '[lint]\nselect = ["F"]\n',
            ".config/ruff-alternate.toml": '[lint]\nselect = ["F"]\n',
            "pyproject.toml": metadata,
            **({"uv.lock": lock} if outcome != "lock-missing" else {}),
            "src/app.py": "def answer():\n    return 42\n",
            "tests/test_app.py": (
                "from src.app import answer\n\ndef test_answer(subtests):\n"
                "    for expected in (42, 42):\n"
                "        with subtests.test(expected=expected):\n"
                "            assert answer() == expected\n"
            ),
        },
    )
    supply.bind(repo)
    outputs = (
        {"path": "nox.json", "format": "nox-json", "sessions": (behavior, static)},
        {"path": "behavior.xml", "format": "junit-xml", "sessions": (behavior,)},
        {"path": "behavior-events.jsonl", "format": "pytest-jsonl", "sessions": (behavior,)},
        {"path": "coverage.xml", "format": "cobertura-xml", "sessions": (behavior,)},
        {"path": "ruff.sarif", "format": "sarif", "sessions": (static,)},
        {
            "path": "behavior-runtime.json",
            "configuration": ".config/pytest/pytest.toml",
            "format": "python-runtime-json",
            "sessions": (behavior,),
            "python": version,
            "dependency_groups": ("absent",) if outcome == "group-missing" else ("dev",),
        },
        {
            "path": "static-runtime.json",
            "configuration": ".config/ruff.toml",
            "format": "python-runtime-json",
            "sessions": (static,),
            "python": version,
            "dependency_groups": ("absent",) if outcome == "group-missing" else ("dev",),
        },
    )
    return Gate.model_validate(
        {
            "id": "native-python",
            "kind": "test",
            "command": (
                str(supply.parent),
                "-B",
                "-I",
                "-m",
                "nox",
                "--non-interactive",
                "--nocolor",
                "-f",
                str(repo / "noxfile.py"),
                "-s",
                behavior,
                static,
                "--report",
                "{native_output}/nox.json",
            ),
            "verification_providers": (
                "ethos.adapters.gates.python_quality:behavior_report",
                "ethos.adapters.gates.python_quality:static_report",
            ),
            "native_outputs": outputs,
            "timeout_seconds": 15 if outcome == "timeout" else 45,
        }
    )
