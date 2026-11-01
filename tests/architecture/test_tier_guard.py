"""The tier guard reports what each case crosses without changing any outcome."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
_UNIT = """\
def test_reads_a_file(tmp_path):
    (tmp_path / "read.txt").write_text("x", encoding="utf-8")


def test_imports_lazily():
    import json.tool


def test_fails_after_reading(tmp_path):
    (tmp_path / "failed.txt").write_text("x", encoding="utf-8")
    raise AssertionError("kept")
"""
_INTEGRATION = """\
import socket


def test_connects_to_loopback():
    with socket.create_server(("127.0.0.1", 0)) as server:
        socket.create_connection(server.getsockname()).close()
"""


def test_guard_records_crossings_and_keeps_outcomes(tmp_path: Path) -> None:
    """A unit case's file read exceeds its tier; imports and loopback connections do not."""
    for relative, text in (
        ("tests/unit/test_cases.py", _UNIT),
        ("tests/integration/test_net.py", _INTEGRATION),
    ):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(text, encoding="utf-8")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    junit = tmp_path / "junit.xml"

    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "tests.support.tier_guard",
            "-q",
            "-o",
            f"cache_dir={tmp_path / 'cache'}",
            f"--junitxml={junit}",
            "tests",
        ),
        cwd=tmp_path,
        env={**environment, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 1, completed.stdout + completed.stderr
    cases = {
        case.get("name"): (
            {item.get("name"): item.get("value") for item in case.iter("property")},
            case.find("failure") is not None,
        )
        for case in ElementTree.parse(junit).getroot().iter("testcase")
    }
    assert cases == {
        "test_reads_a_file": ({"ethos.crossed": "open", "ethos.exceeds": "true"}, False),
        "test_imports_lazily": ({}, False),
        "test_fails_after_reading": ({"ethos.crossed": "open", "ethos.exceeds": "true"}, True),
        "test_connects_to_loopback": (
            {"ethos.crossed": "socket.connect", "ethos.exceeds": "false"},
            False,
        ),
    }
