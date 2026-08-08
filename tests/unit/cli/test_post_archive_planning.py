from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_plan_admits_the_exact_post_archive_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(
        tmp_path,
        scope=("openspec/changes/fixture-change/**",),
    )
    worktree = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "complete fixture change")
    completed = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=completed,
    )
    assert advanced["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    archived = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed,
        apply=True,
    )
    assert archived["verdict"] == "pass", archived

    payload = run_ethos("plan", "--changed", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["verdict"] == "pass", payload
    authority = payload["data"]["transition_plan"]["prior_attestations"]["openspec_archive"]
    assert authority["predicate"] == "effect:openspec-archive"
