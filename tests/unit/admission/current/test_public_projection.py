from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo
from tests.support.lane_scenarios import leased_worktree

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("actor", "gap", "decision_state"),
    [
        (None, "invocation_actor_missing:work/feature", "automatic"),
        ("agent:test:case:other", "lease_holder_mismatch:work/feature", "await-user"),
    ],
)
def test_public_surfaces_preserve_one_current_authority_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    actor: str | None,
    gap: str,
    decision_state: str,
) -> None:
    lane = leased_worktree(
        init_git_repo(tmp_path / "repo"),
        tmp_path / "repo-work-feature",
    )
    if actor is None:
        monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    else:
        monkeypatch.setenv("ETHOS_ACTOR", actor)
    path = "README.md"
    editor_root = lane.resolve().as_posix()

    results = (
        run_ethos("status", "--json", cwd=lane),
        run_ethos("plan", "--changed", "--json", cwd=lane),
        run_ethos_blocked(
            "lane",
            "prewrite",
            path,
            "--editor-root",
            editor_root,
            "--require-editor-root",
            "--json",
            cwd=lane,
        ),
        run_ethos_blocked(
            "hook",
            "admit",
            "pre-tool",
            path,
            "--editor-root",
            editor_root,
            "--require-editor-root",
            "--json",
            cwd=lane,
        ),
        run_ethos_blocked("prove", "--json", cwd=lane),
    )

    assert {result["required_gaps"][0] for result in results} == {gap}
    assert {result["next_action"] for result in results} == {
        "export ETHOS_ACTOR=agent:test:case:agent-a"
    }
    assert {result["user_decision_required"] for result in results} == {
        decision_state == "await-user"
    }
