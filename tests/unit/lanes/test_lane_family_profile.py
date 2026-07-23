from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lanes as lanes
from ethos.adapters.mutation.lanes import start_work_lane
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


_HOLDER = "agent:test:case:agent-test"


def _enable(repo: Path) -> None:
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.write_text("[branch_roles]\nrepository_family_worktrees = true\n", encoding="utf-8")


def test_family_profile_uses_date_bound_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    _enable(repo)
    monkeypatch.setattr(lanes, "utc_now", lambda: datetime(2026, 7, 22, tzinfo=UTC))
    report = start_work_lane(root=repo, name="ownerless closeout admission", holder_ref=_HOLDER)
    lane_id = "20260722-ownerless-closeout-admission"
    assert report["branch"] == f"work/{lane_id}"
    assert report["path"] == (tmp_path / "repo-worktrees" / lane_id).as_posix()


def test_family_profile_rejects_noncanonical_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    _enable(repo)
    report = start_work_lane(
        root=repo, name="feature", path=tmp_path / "outside", holder_ref=_HOLDER, apply=True
    )
    assert report["ok"] is False
    assert report["required_gaps"] == ["work_lane_path_not_canonical"]


def test_family_profile_requires_the_canonical_work_branch_prefix(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos/workspace.toml").write_text(
        '[branch_roles]\nrepository_family_worktrees = true\nwork_branch_prefix = "lane/"\n',
        encoding="utf-8",
    )

    report = start_work_lane(root=repo, name="feature", holder_ref=_HOLDER)

    assert report["ok"] is False
    assert report["required_gaps"] == ["repository_family_profile_requires_work_branch_prefix"]
