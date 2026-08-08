from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.ethos_cli_runner import run_ethos_raw


def test_lane_retire_help_exposes_only_bounded_retirement_commands() -> None:
    completed = run_ethos_raw("lane", "retire", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "landed" in completed.stdout
    assert "superseded" in completed.stdout
    assert "absorbed-ref" in completed.stdout
    assert "reconcile-ref-absent" not in completed.stdout
    assert "retire-unbound" not in completed.stdout


@pytest.mark.parametrize("command", ["unbound", "reconcile-ref-absent"])
def test_removed_retirement_commands_have_no_forwarding_surface(command: str) -> None:
    completed = run_ethos_raw("lane", "retire", command, "--help")

    assert completed.returncode != 0


def test_unbound_retirement_implementation_is_removed() -> None:
    root = Path(__file__).resolve().parents[4]
    unbound_root = root / "src/ethos/adapters/mutation/lane_retirement/unbound"

    assert not tuple(unbound_root.rglob("*.py"))


def test_absorbed_ref_requires_exact_ancestor_and_unbound_confirmation() -> None:
    """The narrow absorbed-ref route is the only bounded unbound retirement surface."""
    completed = run_ethos_raw("lane", "retire", "absorbed-ref", "--help")

    assert completed.returncode == 0, completed.stderr
    for option in (
        "--branch",
        "--expect-head",
        "--accepted-head",
        "--authorize",
        "--confirm-irreversible",
        "--apply",
    ):
        assert option in completed.stdout
