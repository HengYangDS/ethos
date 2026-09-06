from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.ini"


def test_parallel_python_test_gate_does_not_replay_a_crashed_worker(tmp_path: Path) -> None:
    marker = tmp_path / "executions.txt"
    test = tmp_path / "test_worker_loss.py"
    test.write_text(
        """import os
from pathlib import Path


def test_worker_loss() -> None:
    marker = Path(os.environ["ETHOS_WORKER_LOSS_MARKER"])
    with marker.open("ab", buffering=0) as stream:
        stream.write(b"executed\\n")
    os._exit(86)
""",
        encoding="utf-8",
    )
    command = [sys.executable, "-m", "pytest", "-c", str(PYTEST_CONFIG)]
    command += ["-n", "2", str(test)]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=os.environ | {"ETHOS_WORKER_LOSS_MARKER": str(marker)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert marker.read_text(encoding="utf-8") == "executed\n"
    output = result.stdout + result.stderr
    for fragment in ("worker 'gw", "crashed while running", "::test_worker_loss"):
        assert fragment in output
