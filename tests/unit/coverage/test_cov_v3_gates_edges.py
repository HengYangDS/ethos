"""Behavioral edge matrix for the checkout-local ty gate."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from ethos.adapters.gates import ty as ty_mod
from ethos.adapters.gates.ty import ty_gate_report

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

PACKAGE = "packages/rt"


def _policy(root: Path, *packages: str) -> None:
    path = root / ".config/checks/ty/policy.toml"
    path.parent.mkdir(parents=True)
    path.write_text(f"[zero_tolerance]\npackages = {list(packages)!r}\n", encoding="utf-8")


def _completed(*, stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _diagnostic(package: str, count: int) -> dict[str, object]:
    return {
        "count": count,
        "returncode": int(bool(count)),
        "state": "diagnostics" if count else "clean",
        "command": f"ty check {package}",
        "diagnostic_excerpt": [],
    }


def test_ty_gate_policy_and_package_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = ty_gate_report(tmp_path)
    assert (missing["ok"], missing["state"], missing["required_gaps"]) == (
        False,
        "blocked",
        ["ty_policy_missing"],
    )

    _policy(tmp_path, "packages/zt", PACKAGE)
    counts = {"packages/zt/src": 3, "packages/rt/src": 5}
    monkeypatch.setattr(
        ty_mod, "_diagnostic_report", lambda _root, package: _diagnostic(package, counts[package])
    )
    blocked = ty_gate_report(tmp_path)
    assert blocked["required_gaps"] == [
        "ty_zero_tolerance_violation:packages/zt:3",
        "ty_zero_tolerance_violation:packages/rt:5",
    ]

    monkeypatch.setattr(
        ty_mod, "_diagnostic_report", lambda _root, package: _diagnostic(package, 0)
    )
    clean = ty_gate_report(tmp_path)
    assert (
        clean["ok"],
        clean["state"],
        clean["required_gaps"],
        clean["packages"][PACKAGE]["count"],
    ) == (True, "clean", [], 0)


def test_ty_runtime_command_and_result_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _policy(tmp_path, PACKAGE)
    cases = (
        (_completed(stdout="All checks passed!"), ([], "clean", 0, 0, ["All checks passed!"])),
        (
            _completed(stdout="All checks passed!", returncode=1),
            (["ty_execution_failed:packages/rt:1"], "tool_error", 0, 1, ["All checks passed!"]),
        ),
        (
            _completed(stderr="python: No module named ty", returncode=1),
            (
                ["ty_execution_failed:packages/rt:1"],
                "tool_error",
                None,
                1,
                ["python: No module named ty"],
            ),
        ),
        (
            _completed(stdout="error[not-iterable]: bad\n\nFound 5 diagnostics\n", returncode=1),
            (
                ["ty_zero_tolerance_violation:packages/rt:5"],
                "diagnostics",
                5,
                1,
                ["error[not-iterable]: bad", "Found 5 diagnostics"],
            ),
        ),
        (
            OSError("type runtime unavailable"),
            (
                ["ty_execution_failed:packages/rt:launch"],
                "tool_error",
                None,
                None,
                ["OSError: type runtime unavailable"],
            ),
        ),
    )
    calls: list[list[str]] = []
    for outcome, expected in cases:

        def run(args: list[str], _outcome: object = outcome, **_kwargs: object) -> SimpleNamespace:
            calls.append(list(args))
            if isinstance(_outcome, BaseException):
                raise _outcome
            assert isinstance(_outcome, SimpleNamespace)
            return _outcome

        monkeypatch.setattr(ty_mod.subprocess, "run", run)
        report = ty_gate_report(tmp_path)
        package = report["packages"][PACKAGE]
        assert (
            report["required_gaps"],
            package["state"],
            package["count"],
            package["returncode"],
            package["diagnostic_excerpt"],
        ) == expected
        assert package["command"] == "ty check packages/rt/src"

    expected_prefix = [
        str(tmp_path / "tools/ci/scripts/with-python-runtime.sh"),
        "--",
        "uv",
        "run",
        "--locked",
        "--all-packages",
        "--group",
        "dev",
        "python",
        "-m",
        "ty",
        "check",
        "--python",
    ]
    assert calls[0][: len(expected_prefix)] == expected_prefix
    assert calls[0][len(expected_prefix) :] == [
        str(tmp_path / "build/runtime/venv"),
        "--extra-search-path",
        str(tmp_path / "packages/ethos-core/src"),
        "--extra-search-path",
        str(tmp_path / "packages/ethos/src"),
        "packages/rt/src",
    ]
