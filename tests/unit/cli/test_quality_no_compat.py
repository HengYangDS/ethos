from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_quality_no_compat_command_reports_clean_current_product() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ethos.cli",
            "quality",
            "no-compat",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["state"] == "clean"
    assert payload["summary"]["finding_count"] == 0
