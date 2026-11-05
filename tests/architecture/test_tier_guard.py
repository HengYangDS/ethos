"""The tier guard reports what each case crosses without changing any outcome."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
_UNIT = """\
import os

import pytest
from hypothesis import given
from hypothesis import strategies


@pytest.fixture
def prepared(tmp_path):
    (tmp_path / "setup.txt").write_text("x", encoding="utf-8")


@pytest.fixture
def cleaned(tmp_path):
    yield
    (tmp_path / "teardown.txt").write_text("x", encoding="utf-8")


@pytest.fixture(scope="session")
def shared(tmp_path_factory):
    (tmp_path_factory.mktemp("shared") / "shared.txt").write_text("x", encoding="utf-8")


def test_prepares_a_file(prepared):
    pass


def test_cleans_up_a_file(cleaned):
    pass


def test_shares_a_session_fixture(shared):
    pass


def test_moves_and_removes(tmp_path):
    (tmp_path / "a").write_text("x", encoding="utf-8")
    (tmp_path / "a").rename(tmp_path / "b")
    (tmp_path / "b").unlink()


def test_runs_a_shell():
    assert os.system("exit 0") == 0


@given(strategies.integers())
def test_generates_values(value):
    assert isinstance(value, int)


def test_reads_a_file(tmp_path):
    (tmp_path / "read.txt").write_text("x", encoding="utf-8")


def test_imports_lazily():
    import json.tool


def test_reads_package_metadata():
    from importlib import metadata

    assert metadata.distribution("pytest").read_text("METADATA")


def test_fails_after_reading(tmp_path):
    (tmp_path / "failed.txt").write_text("x", encoding="utf-8")
    raise AssertionError("kept")
"""
_INTEGRATION = """\
import socket


def test_connects_to_loopback():
    with socket.create_server(("localhost", 0)) as server:
        socket.create_connection(server.getsockname()).close()
"""


def test_guard_records_crossings_and_keeps_outcomes(tmp_path: Path) -> None:
    """Each phase's crossings are a case's own; loading, tools and wider fixtures are not."""
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
        env={
            **environment,
            "PYTHONPATH": str(ROOT),
            "HYPOTHESIS_STORAGE_DIRECTORY": str(tmp_path / "hypothesis"),
        },
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
    exceeds = {"ethos.exceeds": "true"}
    assert cases == {
        "test_prepares_a_file": ({"ethos.crossed": "open", **exceeds}, False),
        "test_cleans_up_a_file": ({"ethos.crossed": "open", **exceeds}, False),
        "test_shares_a_session_fixture": ({}, False),
        "test_moves_and_removes": (
            {"ethos.crossed": "open,os.remove,os.rename", **exceeds},
            False,
        ),
        "test_runs_a_shell": ({"ethos.crossed": "os.system", **exceeds}, False),
        "test_generates_values": ({}, False),
        "test_reads_a_file": ({"ethos.crossed": "open", "ethos.exceeds": "true"}, False),
        "test_imports_lazily": ({}, False),
        "test_reads_package_metadata": ({"ethos.crossed": "open,os.listdir", **exceeds}, False),
        "test_fails_after_reading": ({"ethos.crossed": "open", "ethos.exceeds": "true"}, True),
        "test_connects_to_loopback": (
            {"ethos.crossed": "socket.connect", "ethos.exceeds": "false"},
            False,
        ),
    }
