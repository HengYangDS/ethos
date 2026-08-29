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
    ("outcome", "gap", "state", "count"),
    [
        (OSError("unavailable"), "ty_execution_failed:.:launch", "tool_error", None),
        (
            subprocess.CompletedProcess([], 2, "", "fatal startup"),
            "ty_execution_failed:.:2",
            "tool_error",
            None,
        ),
        (
            subprocess.CompletedProcess([], 1, "Found 2 diagnostics", "detail"),
            "ty_zero_tolerance_violation:.:2",
            "diagnostics",
            2,
        ),
        (subprocess.CompletedProcess([], 0, "All checks passed", ""), "", "clean", 0),
    ],
)
def test_ty_gate_classifies_tool_and_diagnostic_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: subprocess.CompletedProcess[str] | OSError,
    gap: str,
    state: str,
    count: int | None,
) -> None:
    policy = tmp_path / ".config/checks/ty/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text('[zero_tolerance]\npackages = ["."]\n', encoding="utf-8")

    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, OSError):
            raise outcome
        return outcome

    monkeypatch.setattr(ty.subprocess, "run", run)

    report = ty.ty_gate_report(tmp_path)

    assert report["required_gaps"] == ([gap] if gap else [])
    package = report["packages"]["."]
    assert (package["state"], package["count"]) == (state, count)
    if isinstance(outcome, OSError):
        assert package["diagnostic_excerpt"] == ["OSError: unavailable"]
