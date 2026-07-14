"""Coverage-closure v3: gates reachable branches (100% no-exemption)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ethos.adapters.gates import ty as ty_mod
from ethos.adapters.gates.ty import ty_gate_report

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write_policy(root: Path, toml: str) -> None:
    policy_path = root / ".config" / "checks" / "ty" / "policy.toml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(toml, encoding="utf-8")


def _zero_policy(*packages: str) -> str:
    return "[zero_tolerance]\npackages = [" + ", ".join(map(repr, packages)) + "]\n"


def _fake_diagnostic_report(root: Path, package_src: str) -> dict[str, object]:
    # packages/zt yields 3 and packages/rt yields 5 diagnostics.
    assert root.exists()
    count = 3 if package_src.startswith("packages/zt") else 5
    return {
        "count": count,
        "returncode": 1,
        "state": "diagnostics",
        "command": f"ty check {package_src}",
        "diagnostic_excerpt": [f"Found {count} diagnostics"],
    }


# ---------------------------------------------------------------------------
# ethos.adapters.gates.ty
# ---------------------------------------------------------------------------


def test_ty_gate_report_blocks_when_policy_missing(tmp_path: Path) -> None:
    # No .config/checks/ty/policy.toml -> early blocked return (ty.py 42->43, 43-48).
    report = ty_gate_report(tmp_path)

    assert (report["ok"], report["state"]) == (False, "blocked")
    assert report["required_gaps"] == ["ty_policy_missing"]


def test_ty_gate_report_flags_zero_tolerance_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any diagnostic in a governed package blocks the type gate."""
    _write_policy(tmp_path, _zero_policy("packages/zt", "packages/rt"))
    monkeypatch.setattr(ty_mod, "_diagnostic_report", _fake_diagnostic_report)

    report = ty_gate_report(tmp_path)

    assert report["required_gaps"] == [
        "ty_zero_tolerance_violation:packages/zt:3",
        "ty_zero_tolerance_violation:packages/rt:5",
    ]
    assert (report["ok"], report["state"]) == (False, "blocked")


def test_ty_gate_report_invokes_ty_through_active_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_policy(tmp_path, _zero_policy("packages/rt"))
    calls: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = "All checks passed!"
        stderr = ""

    def run(args, **_kwargs):
        calls.append(list(args))
        return Completed()

    monkeypatch.setattr(ty_mod.subprocess, "run", run)

    report = ty_gate_report(tmp_path)

    assert report["ok"] is True
    assert calls == [
        [
            sys.executable,
            "-m",
            "ty",
            "check",
            "--python",
            str(tmp_path / "build" / "runtime" / "venv"),
            "packages/rt/src",
        ]
    ]


def test_ty_gate_report_exposes_command_and_diagnostic_excerpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_policy(tmp_path, _zero_policy("packages/rt"))

    class Completed:
        returncode = 1
        stdout = "error[not-iterable]: object is not iterable\n\nFound 5 diagnostics\n"
        stderr = ""

    monkeypatch.setattr(ty_mod.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = ty_gate_report(tmp_path)
    package = report["packages"]["packages/rt"]

    assert package["command"] == "ty check packages/rt/src"
    assert package["diagnostic_excerpt"] == [
        "error[not-iterable]: object is not iterable",
        "Found 5 diagnostics",
    ]


def test_ty_gate_report_blocks_nonzero_exit_even_with_clean_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit status is authoritative; success text cannot mask a failed process."""
    _write_policy(tmp_path, _zero_policy("packages/zt"))

    class Completed:
        returncode = 1
        stdout = "All checks passed!\n"
        stderr = ""

    monkeypatch.setattr(ty_mod.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = ty_gate_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["ty_execution_failed:packages/zt:1"]
    assert report["packages"]["packages/zt"]["state"] == "tool_error"


def test_ty_gate_report_blocks_indeterminate_tool_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing type checker is a blocked gate, never a zero-diagnostic pass."""
    _write_policy(tmp_path, _zero_policy("packages/zt"))

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "python: No module named ty\n"

    monkeypatch.setattr(ty_mod.subprocess, "run", lambda *_args, **_kwargs: Completed())

    report = ty_gate_report(tmp_path)
    package = report["packages"]["packages/zt"]

    assert (report["ok"], report["state"]) == (False, "blocked")
    assert report["required_gaps"] == ["ty_execution_failed:packages/zt:1"]
    assert package["state"] == "tool_error"
    assert package["count"] is None
    assert package["diagnostic_excerpt"] == ["python: No module named ty"]


def test_ty_gate_report_blocks_tool_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An execution exception becomes a structured blocking result."""
    _write_policy(tmp_path, _zero_policy("packages/zt"))

    def raise_launch_failure(*_args: object, **_kwargs: object) -> None:
        message = "type runtime unavailable"
        raise OSError(message)

    monkeypatch.setattr(ty_mod.subprocess, "run", raise_launch_failure)

    report = ty_gate_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["ty_execution_failed:packages/zt:launch"]
    package = report["packages"]["packages/zt"]
    assert package["state"] == "tool_error"
    assert package["returncode"] is None
    assert package["diagnostic_excerpt"] == ["OSError: type runtime unavailable"]


def test_ty_gate_report_allows_zero_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A governed package passes only when its determinate count is zero."""
    _write_policy(tmp_path, _zero_policy("packages/zt", "packages/rt"))

    def diagnostic_report(_root: Path, package_src: str) -> dict[str, object]:
        return {
            "count": 0,
            "returncode": 0,
            "state": "clean",
            "command": f"ty check {package_src}",
            "diagnostic_excerpt": [],
        }

    monkeypatch.setattr(ty_mod, "_diagnostic_report", diagnostic_report)

    report = ty_gate_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["required_gaps"] == []
    assert report["packages"]["packages/rt"]["count"] == 0
