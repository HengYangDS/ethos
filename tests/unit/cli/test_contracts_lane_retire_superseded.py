from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import superseded_work_lane

_ACTOR = "agent:test:case:agent-a"
_SUPERSEDED_BRANCH = "work/superseded"


def _retire_superseded(runner, repo: Path, head: str, absorbed_by: str) -> dict[str, object]:
    return runner(
        "lane",
        "retire",
        "superseded",
        "--branch",
        _SUPERSEDED_BRANCH,
        "--expect-head",
        head,
        "--absorbed-by",
        absorbed_by,
        "--reason",
        "accepted root already carries the semantic fix",
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )


def test_lane_retire_superseded_apply_removes_absorbed_linked_lane(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, worktree, worktree_head, accepted_head, _database = superseded_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)

    payload = _retire_superseded(run_ethos, repo, worktree_head, accepted_head)

    assert payload["command"] == "lane retire superseded"
    assert payload["ok"] is True
    assert payload["state"] == "retired_superseded"
    assert payload["summary"] == {
        "branch": "work/superseded",
        "head": worktree_head,
        "absorbed_by": accepted_head,
        "retire_ready": True,
    }
    assert payload["data"]["mutation"]["request"]["expect_head"] == worktree_head
    assert not worktree.exists()


@pytest.mark.parametrize(
    ("case", "absorbed_by", "expected_gap"),
    [
        ("unabsorbed", "", "superseded_lane_not_absorbed_by_accepted"),
        ("absorbed", "old-head", "absorbed_by_not_current_accepted_head"),
    ],
    ids=("unabsorbed-linked-lane", "stale-absorption-head"),
)
def test_lane_retire_superseded_blocks_without_current_absorption_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    absorbed_by: str,
    expected_gap: str,
) -> None:
    repo, worktree, worktree_head, accepted_head, _database = superseded_work_lane(
        tmp_path, absorbed=case == "absorbed"
    )
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    payload = _retire_superseded(
        run_ethos_blocked,
        repo,
        worktree_head,
        absorbed_by or accepted_head,
    )

    assert payload["command"] == "lane retire superseded"
    assert payload["ok"] is False
    assert payload["required_gaps"] == [expected_gap]
    assert worktree.exists()
