"""A suite leg repeats the suite through the shipped probe and fails with it."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from tests.support.nox_session import SessionDouble
from tools.ci import sessions


@pytest.mark.parametrize(
    ("verdict", "diagnostics", "named"),
    [
        ("pass", None, ""),
        # A failed suite has its output in the log and no diagnostics: the error ends at the gap.
        ("block", None, r"suite leg failed: \['a_gap'\]$"),
        # A refusal that never reached pytest has no output: the error names its diagnostics.
        ("block", [{"cause": "why"}], r"suite leg failed: \['a_gap'\] \[\{'cause': 'why'\}\]$"),
    ],
)
def test_a_suite_leg_runs_the_probe_as_a_leg_within_the_named_deadline(
    tmp_path, monkeypatch, verdict, diagnostics, named
) -> None:
    """The probe finds the repository's Mise first on its path; a leg that does not pass fails."""
    report = {"verdict": verdict, "required_gaps": ["a_gap"]}
    report |= {"diagnostics": diagnostics} if diagnostics else {}
    opened: list[object] = []

    @contextmanager
    def scope(*, timeout_seconds):
        opened.append(timeout_seconds)
        yield
        opened.append("closed")

    # The stub's output is the path and the deadline scope it ran under, which the session logs.
    probe = Mock(
        side_effect=lambda *_a, **_k: (
            report | {"native": {"stdout": f"{os.environ['PATH']} {opened}"}}
        )
    )
    monkeypatch.setattr("ethos.adapters.process.command_scope", scope)
    monkeypatch.setenv("PATH", "host")
    monkeypatch.setattr("tools.ci.toolchain.native.prepare_mise", lambda _root: tmp_path / "mise")
    monkeypatch.setattr("ethos.adapters.gates.python_quality.behavior_report", probe)
    session = SessionDouble(posargs=("7200",))

    if verdict == "pass":
        sessions.suite_leg(session)
    else:
        with pytest.raises(pytest.fail.Exception, match=named):
            sessions.suite_leg(session)

    probe.assert_called_once_with(sessions.ROOT, timeout_seconds=7200, leg=True)
    # One deadline bounds the leg's sync and its suite together: the probe ran inside it.
    assert session.logs == [(f"Python {sys.version}\n{tmp_path}{os.pathsep}host [7200.0]",)]
