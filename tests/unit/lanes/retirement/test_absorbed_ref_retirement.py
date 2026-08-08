from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.absorbed as absorbed_retirement
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _absorbed_ref(tmp_path: Path) -> tuple[Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    source = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "work/absorbed", source)
    marker = repo / "accepted.txt"
    marker.write_text("accepted\n", encoding="utf-8")
    git(repo, "add", marker.name)
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance accepted truth",
    )
    return repo, source, git(repo, "rev-parse", "HEAD")


def test_absorbed_ref_retires_exact_unbound_unleased_ancestor(tmp_path: Path) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    arguments = (
        "lane",
        "retire",
        "absorbed-ref",
        "--branch",
        "work/absorbed",
        "--expect-head",
        source,
        "--accepted-head",
        accepted,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--confirm-irreversible",
        "--json",
    )

    planned = run_ethos(*arguments, cwd=repo)
    assert (planned["verdict"], planned["state"], planned["required_gaps"]) == (
        "pass",
        "ready_to_retire_absorbed_ref",
        [],
    )
    applied = run_ethos(*arguments, "--apply", cwd=repo)

    assert (applied["verdict"], applied["state"], applied["required_gaps"]) == (
        "pass",
        "retired_absorbed_ref",
        [],
    )
    receipt = applied["data"]["retired"]
    assert receipt == {
        "branch": "work/absorbed",
        "head": source,
        "accepted_head": accepted,
        "ref_state": "absent",
        "worktree_binding": "absent",
        "lease_state": "missing",
    }
    assert git(repo, "branch", "--list", "work/absorbed") == ""
    assert observe_lease(state_database(repo), "work/absorbed").state == "missing"


def test_absorbed_ref_fails_closed_when_ref_is_not_an_accepted_ancestor(tmp_path: Path) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    git(repo, "branch", "-f", "work/absorbed", accepted)
    changed = git(repo, "rev-parse", "work/absorbed")

    payload = run_ethos_blocked(
        "lane",
        "retire",
        "absorbed-ref",
        "--branch",
        "work/absorbed",
        "--expect-head",
        changed,
        "--accepted-head",
        source,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--confirm-irreversible",
        "--apply",
        "--json",
        cwd=repo,
    )

    assert "accepted_head_mismatch" in payload["required_gaps"]
    assert git(repo, "rev-parse", "work/absorbed") == changed


def test_absorbed_ref_reobserves_before_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, source, accepted = _absorbed_ref(tmp_path)
    original = absorbed_retirement.workspace_status
    calls = 0

    def worktree_appeared(root: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        status = original(root)
        if calls == 2:
            worktrees = cast("list[dict[str, object]]", status["worktrees"])
            status["worktrees"] = [
                *worktrees,
                {"branch": "work/absorbed", "path": "/appeared"},
            ]
        return status

    monkeypatch.setattr(absorbed_retirement, "workspace_status", worktree_appeared)
    payload = run_ethos_blocked(
        "lane",
        "retire",
        "absorbed-ref",
        "--branch",
        "work/absorbed",
        "--expect-head",
        source,
        "--accepted-head",
        accepted,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--confirm-irreversible",
        "--apply",
        "--json",
        cwd=repo,
    )

    assert payload["required_gaps"] == ["absorbed_ref_worktree_appeared"]
    assert git(repo, "rev-parse", "work/absorbed") == source
