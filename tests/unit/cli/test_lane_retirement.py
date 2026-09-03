from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos_raw


def test_superseded_retirement_exposes_exact_missing_worktree_recovery_path() -> None:
    completed = run_ethos_raw("lane", "retire", "superseded", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "--path" in completed.stdout


def test_retirement_help_exposes_abandonment_and_one_recovery_route() -> None:
    completed = run_ethos_raw("lane", "retire", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "abandon" in completed.stdout
    assert "recover" in completed.stdout
