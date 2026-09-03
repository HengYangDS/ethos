from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.python_test_gate as python_test_gate

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]


def test_parallel_python_test_gate_does_not_replay_a_crashed_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "executions.txt"
    crashing_test = tmp_path / "test_worker_loss.py"
    crashing_test.write_text(
        """import os
from pathlib import Path


def test_worker_loss() -> None:
    marker = Path(os.environ["ETHOS_WORKER_LOSS_MARKER"])
    with marker.open("a", encoding="utf-8") as stream:
        stream.write("executed\\n")
        stream.flush()
        os.fsync(stream.fileno())
    os._exit(86)
""",
        encoding="utf-8",
    )
    settings = python_test_gate.Settings(
        head="a" * 40,
        evidence=tmp_path / "evidence",
        basetemp=tmp_path / "pytest",
        basetemp_owned=True,
        workers=2,
        shards=None,
        durations=0,
        timeout=None,
        lock_wait=0,
        uv_cache=None,
        node_package_supply=tmp_path / "node_modules",
        identity=None,
    )
    gate = python_test_gate.PythonTestGate(settings)
    result: subprocess.CompletedProcess[str] | None = None

    class Session:
        @staticmethod
        def run(*command: str, **kwargs: object) -> None:
            nonlocal result
            environment = os.environ.copy()
            for name in (
                "COV_CORE_CONFIG",
                "COV_CORE_DATAFILE",
                "COV_CORE_SOURCE",
                "PYTEST_ADDOPTS",
                "PYTEST_CURRENT_TEST",
                "PYTEST_XDIST_TESTRUNUID",
                "PYTEST_XDIST_WORKER",
                "PYTEST_XDIST_WORKER_COUNT",
            ):
                environment.pop(name, None)
            for name, value in cast("dict[str, str | None]", kwargs["env"]).items():
                if value is None:
                    environment.pop(name, None)
                else:
                    environment[name] = value
            environment["ETHOS_WORKER_LOSS_MARKER"] = str(marker)
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                message = "nested pytest failed"
                raise RuntimeError(message)

    monkeypatch.setattr(python_test_gate, "TARGETS", (str(crashing_test),))
    monkeypatch.setattr(python_test_gate, "_head", lambda: settings.head)
    with pytest.raises(RuntimeError, match="nested pytest failed"):
        gate.run_tests(cast("nox.Session", Session()))

    assert result is not None
    assert result.returncode != 0
    assert marker.read_text(encoding="utf-8") == "executed\n"
    output = result.stdout + result.stderr
    assert "worker 'gw" in output
    assert "crashed while running" in output
    assert "::test_worker_loss" in output
