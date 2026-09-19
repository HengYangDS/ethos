"""Native type diagnostics cannot become green through prose or a zero exit alone."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.ty as ty

if TYPE_CHECKING:
    from pathlib import Path


def test_ty_gate_requires_policy(tmp_path: Path) -> None:
    assert ty.ty_gate_report(tmp_path) == {
        "verdict": "block",
        "state": "blocked",
        "required_gaps": ["ty_policy_missing"],
        "packages": {},
    }


@pytest.mark.parametrize(
    ("exit_code", "output", "gap", "count"),
    [
        (None, OSError("unavailable"), "ty_execution_failed:.:launch", None),
        (None, subprocess.TimeoutExpired("ty", 120), "ty_execution_failed:.:timeout", None),
        (2, "[]", "ty_execution_failed:.:2", 0),
        (0, "All checks passed", "ty_execution_failed:.:0", None),
        (0, '[{"description":"broken"}]', "ty_execution_failed:.:0", None),
        (0, '["not a diagnostic"]', "ty_execution_failed:.:0", None),
        (0, '[{"description":"broken","severity":[]}]', "ty_execution_failed:.:0", None),
        (1, '[{"description":"finding","severity":"major"}]', "ty_zero_tolerance_violation:.:1", 1),
        (1, '[{"description":"finding","severity":"minor"}]', "ty_zero_tolerance_violation:.:1", 1),
        (0, '[{"description":"finding","severity":"minor"}]', "ty_zero_tolerance_violation:.:1", 1),
        (0, "[]", "", 0),
    ],
)
def test_ty_gate_classifies_tool_and_diagnostic_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code,
    output,
    gap,
    count,
) -> None:
    """Native payload, process status and failure stage have independent expectations."""
    policy = tmp_path / ".config/checks/ty/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text('[zero_tolerance]\npackages = ["."]\n', encoding="utf-8")

    def run(root, command, **kwargs):
        assert root == tmp_path
        assert "--error-on-warning" in command
        assert command[command.index("--output-format") + 1] == "gitlab"
        assert "--frozen" in command
        assert "--offline" in command
        assert kwargs["timeout"] == 120
        if isinstance(output, Exception):
            raise output
        return subprocess.CompletedProcess(command, exit_code, output, "informational output")

    monkeypatch.setattr(ty, "run_command", run)
    report = ty.ty_gate_report(tmp_path)
    assert report["required_gaps"] == ([gap] if gap else [])
    package = report["packages"]["."]
    state = "tool_error" if "execution_failed" in gap else "diagnostics" if gap else "clean"
    assert (package["state"], package["count"]) == (state, count)
    if isinstance(output, OSError):
        assert package["diagnostic_excerpt"] == ["OSError: unavailable"]
