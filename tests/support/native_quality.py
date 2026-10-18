"""Native Nox producer fixtures for public quality-gate tests."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from ethos.contracts.gates import Gate
from tests.support.governed_repository import committed_source_repo


def native_quality_gate(root: Path, outcome: str = "pass") -> Gate:
    """Commit a native Nox producer fixture and return its declared quality gate."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    behavior, static = f"behavior-{version}", f"static-{version}"
    source = f'''"""A native producer for one exact quality attempt."""
import json
import os
from pathlib import Path
import nox

VERSION = {version!r}
EXECUTABLE = {sys.executable!r}
OUTCOME = {outcome!r}

def runtime(session):
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    session.run(EXECUTABLE, "-c",
        "import json,sys; from pathlib import Path; "
        "Path(sys.argv[1]).write_text(json.dumps({{'executable':sys.executable, "
        "'version':list(sys.version_info[:3]), 'prefix':sys.prefix}}))",
        str(output / (session.name + "-runtime.json")), external=True)
    return output

@nox.session(python=VERSION, venv_backend="none")
def behavior(session):
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    if OUTCOME == "runtime-detached":
        runtime(session)
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
    session.run(EXECUTABLE, "-B", "-I", "-m", "pytest", "--rootdir", ".", "-c", config,
        *capture, "-q", "-W", "error",
        "--junitxml=" + str(output / "behavior.xml"),
        "--report-log=" + str(output / "behavior-events.jsonl"), "--cov=src",
        "--cov-branch", "--cov-report=xml:" + str(output / "coverage.xml"),
        "tests", env=env, external=True)

@nox.session(python=VERSION, venv_backend="none")
def static(session):
    output = Path(os.environ["ETHOS_NATIVE_OUTPUT_DIR"])
    record = output / (session.name + "-runtime.json")
    targets = ("src/app.py",) if OUTCOME == "static-scope" else ("src", "tests", "noxfile.py")
    config = ".config/ruff-alternate.toml" if OUTCOME == "static-config" else ".config/ruff.toml"
    binary = Path(EXECUTABLE).with_name("ruff.exe" if os.name == "nt" else "ruff")
    ruff = (str(binary), "check", "--config", config, "--verbose", "--no-cache",
        "--output-format", "sarif", "--output-file", str(output / "ruff.sarif"), *targets)
    if OUTCOME == "static-detached":
        runtime(session)
        session.run(EXECUTABLE, "-m", "ruff", "check", "--config", config,
            "--output-format", "sarif", "--output-file", str(output / "ruff.sarif"),
            "src", "tests", "noxfile.py", external=True)
    else:
        session.run(EXECUTABLE, "-B", "-I", "-m", "ethos.domain.quality.nox", "run",
            "--runtime-output", str(record), "--session", session.name + "-" + VERSION,
            "--configuration", config, "--", *ruff, external=True)
    if OUTCOME == "timeout":
        session.run(EXECUTABLE, "-c",
            "import time; print('timeout-sentinel', flush=True); time.sleep(60)",
            external=True)
    if OUTCOME == "missing":
        (output / "coverage.xml").unlink()
    if OUTCOME == "unsafe-output":
        (output / "coverage.xml").unlink()
        (output / "coverage.xml").mkdir()
    if OUTCOME == "dirty-source":
        with Path("pyproject.toml").open("a") as stream:
            stream.write("\\n")
    if OUTCOME == "advance-head":
        session.run("git", "-c", "user.name=Test User", "-c", "user.email=test@example.com",
            "commit", "--allow-empty", "-m", "advance", external=True)
    if OUTCOME == "commit-change":
        with Path("pyproject.toml").open("a") as stream:
            stream.write("\\n")
        session.run("git", "-c", "user.name=Test User", "-c", "user.email=test@example.com",
            "commit", "-am", "change", external=True)
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
'''
    fixture = Path(__file__).resolve().parents[1] / "fixtures/quality-sample"
    metadata = (fixture / "pyproject.toml").read_text()
    lock = (fixture / "uv.lock").read_text()
    if outcome == "toolchain":
        locked = next(item for item in tomllib.loads(lock)["package"] if item["name"] == "ruff")
        lock = lock.replace(
            f'name = "ruff"\nversion = "{locked["version"]}"',
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
                sys.executable,
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
