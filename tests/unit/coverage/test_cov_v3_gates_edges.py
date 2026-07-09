# ruff: noqa: FLY002
"""Coverage-closure v3: gates reachable branches (100% no-exemption)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ethos.adapters.gates import ty as ty_mod
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.gates.runner import LocalSubprocessRunner
from ethos.adapters.gates.ty import ty_gate_report
from ethos_core.action_graph.core import ActionNode

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _write_policy(root: Path, toml: str) -> None:
    policy_path = root / ".config" / "checks" / "ty" / "policy.toml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(toml, encoding="utf-8")


def _fake_diagnostic_report(root: Path, package_src: str) -> dict[str, object]:
    # zero-tolerance src -> 3 (>0 forces ty.py 57->58); ratchet src -> 5 (>2 forces 62->63).
    assert root.exists()
    count = 3 if package_src.startswith("packages/zt") else 5
    return {
        "count": count,
        "command": f"ty check {package_src}",
        "diagnostic_excerpt": [f"Found {count} diagnostics"],
    }


def _inprocess_decline(node: ActionNode, root: Path) -> ActionRunResult | None:
    # Consulted but declines (returns None) so run() falls through to the subprocess
    # branch — exercises runner.py branch 74->76.
    if node.id == "__never__" or not root.exists():
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            state="failed",
            exit_code=1,
        )
    return None


# ---------------------------------------------------------------------------
# ethos.adapters.gates.ty
# ---------------------------------------------------------------------------


def test_ty_gate_report_blocks_when_policy_missing(tmp_path: Path) -> None:
    # No .config/checks/ty/policy.toml -> early blocked return (ty.py 42->43, 43-48).
    report = ty_gate_report(tmp_path)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["ty_policy_missing"]


def test_ty_gate_report_flags_zero_tolerance_and_ratchet_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # zero-tolerance count>0 appends the violation gap (ty.py 58); ratchet count>baseline
    # appends the exceeded gap (ty.py 63).
    _write_policy(
        tmp_path,
        "\n".join(
            [
                "[zero_tolerance]",
                'packages = ["packages/zt"]',
                "",
                "[ratchet]",
                '"packages/rt" = 2',
                "",
            ]
        ),
    )
    monkeypatch.setattr(ty_mod, "_diagnostic_report", _fake_diagnostic_report)

    report = ty_gate_report(tmp_path)

    assert "ty_zero_tolerance_violation:packages/zt:3" in report["required_gaps"]
    assert "ty_ratchet_exceeded:packages/rt:5>2" in report["required_gaps"]
    assert report["ok"] is False
    assert report["state"] == "blocked"


def test_ty_gate_report_exposes_command_and_diagnostic_excerpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_policy(
        tmp_path,
        "\n".join(
            [
                "[zero_tolerance]",
                "packages = []",
                "",
                "[ratchet]",
                '"packages/rt" = 2',
                "",
            ]
        ),
    )

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


def test_ty_gate_report_allows_counts_at_or_below_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # zero-tolerance count==0 and ratchet count==baseline take the non-gap branches
    # (ty.py 57->59 and 62->59), preserving the frozen ratchet without raising it.
    _write_policy(
        tmp_path,
        "\n".join(
            [
                "[zero_tolerance]",
                'packages = ["packages/zt"]',
                "",
                "[ratchet]",
                '"packages/rt" = 2',
                "",
            ]
        ),
    )

    def count(_root: Path, package_src: str) -> int:
        return 0 if package_src.startswith("packages/zt") else 2

    def diagnostic_report(root: Path, package_src: str) -> dict[str, object]:
        count_value = count(root, package_src)
        return {
            "count": count_value,
            "command": f"ty check {package_src}",
            "diagnostic_excerpt": [],
        }

    monkeypatch.setattr(ty_mod, "_diagnostic_report", diagnostic_report)

    report = ty_gate_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["required_gaps"] == []
    assert report["packages"]["packages/rt"]["count"] == 2


# ---------------------------------------------------------------------------
# ethos.adapters.gates.runner
# ---------------------------------------------------------------------------


def test_local_runner_falls_through_when_handler_declines(tmp_path: Path) -> None:
    # Handler returns None, so `if inprocess is not None` is False and control falls
    # through to the subprocess branch (runner.py 74->76).
    runner = LocalSubprocessRunner(inprocess_handler=_inprocess_decline)
    node = ActionNode(id="probe", kind="check", command=(sys.executable, "-c", "pass"))

    result = runner.run(node, root=tmp_path)

    assert result.state == "passed"
    assert result.exit_code == 0
