"""Exercise same-attempt Nox evidence through the public gate executor."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.python.nox as native_nox
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.gates.verification import NativePythonReports
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "fault", ["none", "unexercised", "all-skipped", "test-failed", "source-changed"]
)
def test_nox_behavior_uses_one_native_attempt_with_real_source_evidence(
    tmp_path: Path, fault: str
) -> None:
    """The native command runs once; unexecuted production code remains unproved."""
    files = {
        "product.py": "def answer():\n    return 42\n",
        "tests/test_product.py": (
            "import sys\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
            "from product import answer\n\ndef test_answer():\n    assert answer() == 42\n"
        ),
        "pyproject.toml": '[project]\nname = "sample"\nversion = "1"\n',
        "uv.lock": "version = 1\n",
        "noxfile.py": (
            "from pathlib import Path\nimport nox\n\n"
            "loaded = Path('module-load-count')\n"
            "loaded.write_text((loaded.read_text() if loaded.exists() else '') + 'x')\n\n"
            "@nox.session(python=False)\ndef tests(session):\n"
            "    marker = Path('attempt-count')\n"
            "    marker.write_text((marker.read_text() if marker.exists() else '') + 'x')\n"
            f"    session.run({sys.executable!r}, '-m', 'pytest', '-q', 'tests', "
            "env={'PYTHONDONTWRITEBYTECODE': '1'})\n"
        ),
    }
    if fault == "unexercised":
        files["unused.py"] = "def unused():\n    return 0\n"
    elif fault == "all-skipped":
        files["tests/test_product.py"] = (
            "import pytest\n\n@pytest.mark.skip(reason='fixture')\n"
            "def test_skipped():\n    assert True\n"
        )
    elif fault == "test-failed":
        files["tests/test_product.py"] = files["tests/test_product.py"].replace("== 42", "== 0")
    elif fault == "source-changed":
        files["noxfile.py"] += "    Path('product.py').write_text('CHANGED = True\\n')\n"
    root = committed_source_repo(tmp_path, files)
    gate = Gate(
        id="python-tests",
        kind="test",
        command=(sys.executable, "-m", "nox", "-s", "tests"),
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))

    result = LocalGateRunner().run(node, gate, root=root)

    assert result.verdict == ("pass" if fault == "none" else "block"), (
        result.diagnostics,
        result.verification,
        result.stdout[-1500:],
        result.stderr[-1500:],
    )
    assert (root / "attempt-count").read_text() == "x"
    assert (root / "module-load-count").read_text() == "x"
    assert result.verification is not None
    assert result.command == gate_execution_identity(gate)


def test_nox_behavior_accepts_exact_installed_artifact_without_source_replay(
    tmp_path: Path,
) -> None:
    """An installed wheel is a valid test subject only through its native source mapping."""
    root = committed_source_repo(
        tmp_path,
        {
            "src/sample/__init__.py": "",
            "src/sample/answer.py": "def answer():\n    return 42\n",
            "src/sample/branch.py": (
                "def branch(value):\n    if value:\n        return 1\n    return 0\n"
            ),
            "tests/test_sample.py": (
                "from sample.answer import answer\nfrom sample.branch import branch\n\n"
                "def test_answer():\n    assert answer() == 42\n    assert branch(True) == 1\n"
            ),
            "pyproject.toml": (
                '[build-system]\nrequires = ["hatchling"]\n'
                'build-backend = "hatchling.build"\n\n'
                '[project]\nname = "sample"\nversion = "1.0"\n\n'
                '[tool.hatch.build.targets.wheel]\npackages = ["src/sample"]\n'
            ),
            "uv.lock": "version = 1\n",
            "noxfile.py": (
                "from pathlib import Path\nimport nox\n\n"
                "@nox.session(python=False)\ndef tests(session):\n"
                "    marker = Path('attempt-count')\n"
                "    marker.write_text((marker.read_text() if marker.exists() else '') + 'x')\n"
                f"    session.run({sys.executable!r}, '-m', 'hatchling', 'build', '-t', 'wheel', "
                "'-d', 'wheelhouse')\n"
                "    wheel = next(Path('wheelhouse').glob('*.whl'))\n"
                f"    session.run({sys.executable!r}, '-m', 'uv', 'pip', 'install', "
                "'--offline', '--no-cache', '--no-config', '--no-deps', "
                "'--target', 'installed', str(wheel))\n"
                f"    session.run({sys.executable!r}, '-m', 'pytest', '-q', 'tests', "
                "env={'PYTHONPATH': str(Path('installed').resolve()), "
                "'PYTHONDONTWRITEBYTECODE': '1'})\n"
            ),
        },
    )
    gate = Gate(
        id="installed-tests",
        kind="test",
        command=(sys.executable, "-m", "nox", "-s", "tests"),
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))

    result = LocalGateRunner().run(node, gate, root=root)

    assert result.verdict == "pass", (result.diagnostics, result.verification)
    assert (root / "attempt-count").read_text() == "x"
    assert result.verification is not None


@pytest.mark.parametrize("fault", ["empty", "missing", "wrong-session", "signature-type"])
def test_native_session_report_rejects_incomplete_or_malformed_scope(
    tmp_path: Path, fault: str
) -> None:
    """A native report must identify every selected session before coverage work."""
    signatures: list[str | None] = [None] if fault == "signature-type" else ["tests"]
    report = {"sessions": [{"result": "success", "signatures": signatures}]}
    if fault == "empty":
        report["sessions"] = []
    elif fault == "wrong-session":
        report["sessions"][0]["signatures"] = ["other"]
    if fault != "missing":
        (tmp_path / "nox.json").write_text(json.dumps(report))
    (tmp_path / "selection.json").write_text(
        json.dumps({"names": ["tests"], "signatures": ["tests"]})
    )
    inputs = NativePythonReports(root=tmp_path, source_digests=(), python_prefix=(sys.executable,))
    execution = NativeExecution(
        declared_identity=(sys.executable,),
        argv=(sys.executable,),
        cwd=tmp_path,
        exit_code=0,
        stdout="",
        stderr="",
        reports=inputs,
    )

    with pytest.raises(ValueError, match="python_nox_session_"):
        native_nox.evidence(tmp_path, execution, ())
