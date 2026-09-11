"""Shared owned divergent-lane setup for retirement observation and recovery cases."""

from __future__ import annotations

import pytest

from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


@pytest.fixture
def divergent_lane(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    lane = tmp_path / "repo-work-abandon"
    git(repo, "worktree", "add", "-b", "work/abandon", str(lane), "dev")
    for root, name in ((repo, "accepted"), (lane, "abandoned")):
        (root / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        commit_fixture(root, f"advance {name} independently")
    actor = "agent:test:case:abandonment-recovery"
    acquire_lease(state_database(repo), lease=exact_lease(branch="work/abandon", holder_ref=actor))
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    return repo, lane
