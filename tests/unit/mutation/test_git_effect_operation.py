"""Name the ref when a candidate integration matches no declared branch role."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

HOLDER = "agent:test:case:agent-test"


def test_unclassified_candidate_integration_names_its_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = start_adopted_candidate(tmp_path)
    lenient = "".join(
        line.replace('"candidate/dev"', '"candidate/train"')
        for line in (repo / ".ethos/workspace.toml").read_text().splitlines(keepends=True)
        if not line.startswith(("release_mirror", "canonical_sibling_worktrees"))
    )
    accepted = commit_fixture_file(repo, ".ethos/workspace.toml", lenient, "record lenient roles")
    hooks = tmp_path / "setup-hooks"
    hooks.mkdir()
    train = tmp_path / "repo-candidate-train"
    git(
        repo,
        "-c",
        f"core.hooksPath={hooks}",
        "worktree",
        "add",
        "-b",
        "candidate/train",
        train.as_posix(),
        accepted,
    )
    worktree = create_change_source_lane(
        repo, tmp_path / "repo-work-train", branch="work/train", holder_ref=HOLDER
    )
    head = commit_fixture_file(
        worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete fixture change",
    )
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)
    seed_executed_proof(worktree, head)
    archived = run_ethos_blocked(
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=worktree,
    )
    assert archived["required_gaps"] == ["proof_not_proven"], archived
    head = git(worktree, "rev-parse", "HEAD")
    seed_executed_proof(worktree, head)

    landed = run_ethos_blocked(
        "land", "--apply", "--authorize", "--expect-head", head, "--json", cwd=worktree
    )

    assert landed["required_gaps"] == ["candidate_update_failed"], landed
    stderr = landed["data"]["candidate_update"]["stderr"]
    assert "ref_transition_operation_unresolved:refs/heads/candidate/train" in stderr
    assert git(train, "rev-parse", "HEAD") == accepted
