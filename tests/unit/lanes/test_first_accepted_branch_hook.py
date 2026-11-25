"""The armed reference-transaction hook admits the first accepted branch and nothing beside it."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.process import run_command
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import RepositorySpec
from tests.support.governed_repository import build
from tests.support.governed_repository import git
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path
    from typing import Any

_REFUSAL = ["candidate_semantic_runner_unavailable"]


def _armed_release_root(tmp_path: Path) -> tuple[Path, str]:
    """A repository adopted while its release branch is its only branch, with its hooks armed."""
    repo = build(
        RepositorySpec(adoption="governance", docs_only=True), tmp_path / "repo"
    ).repository
    git(repo, "branch", "main", "dev")
    git(repo, "checkout", "-q", "main")
    git(repo, "update-ref", "-d", "refs/heads/dev")
    assert install_fixture_hook_runtime(repo)["current"]
    return repo, git(repo, "rev-parse", "main")


def _through_the_hook(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return run_command(repo, ("git", *arguments), timeout=60)


def _gaps(done: subprocess.CompletedProcess[str]) -> list[str]:
    report = next(line for line in done.stderr.splitlines() if line.startswith("{"))
    return json.loads(report)["required_gaps"]


@pytest.mark.parametrize("command", [("switch", "-c", "dev", "main"), ("branch", "dev", "main")])
def test_the_first_accepted_branch_is_created_at_the_release_head(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    repo, head = _armed_release_root(tmp_path)

    done = _through_the_hook(repo, *command)

    assert done.returncode == 0, done.stderr
    assert git(repo, "rev-parse", "refs/heads/dev") == head


def test_a_creation_at_another_commit_keeps_its_refusal(tmp_path: Path) -> None:
    repo, head = _armed_release_root(tmp_path)
    other = git(repo, "commit-tree", f"{head}^{{tree}}", "-p", head, "-m", "not the release head")

    done = _through_the_hook(repo, "branch", "dev", other)

    assert done.returncode != 0
    assert _gaps(done) == _REFUSAL
    assert not git(repo, "for-each-ref", "refs/heads/dev")


@pytest.mark.parametrize(
    "command",
    [
        ("branch", "-f", "dev", "main"),
        ("update-ref", "refs/heads/dev", "main"),
        ("switch", "-C", "dev", "main"),
    ],
)
def test_a_forced_move_of_the_accepted_branch_keeps_its_refusal(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """Git reports such a move with a zero old value, like a creation; the branch is not moved."""
    repo, head = _armed_release_root(tmp_path)
    own = git(repo, "commit-tree", f"{head}^{{tree}}", "-m", "the accepted branch's own")
    git(repo, "update-ref", "refs/heads/dev", own)

    done = _through_the_hook(repo, *command)

    assert done.returncode != 0
    assert _gaps(done) == _REFUSAL
    assert git(repo, "rev-parse", "refs/heads/dev") == own


_CREATE = (
    "create the accepted branch at the release head as an adopted baseline: git switch -c dev main"
)


def _status(repo: Path) -> dict[str, Any]:
    return json.loads(run_ethos_raw("status", "--root", repo.as_posix(), "--json", cwd=repo).stdout)


def test_status_on_the_release_root_names_the_creation(tmp_path: Path) -> None:
    repo, _head = _armed_release_root(tmp_path)

    status = _status(repo)

    assert status["required_gaps"] == ["candidate_branch_missing"]
    assert status["next_action"] == _CREATE
    assert status["next"]["kind"] == "instruction"


def test_status_says_to_fetch_first_where_a_peer_is_configured(tmp_path: Path) -> None:
    repo, _head = _armed_release_root(tmp_path)
    git(repo, "config", "remote.origin.url", "https://peer.invalid/repository.git")
    git(repo, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")

    assert _status(repo)["next_action"] == f"fetch every remote, then {_CREATE}"


def test_status_names_no_creation_that_the_hook_would_refuse(tmp_path: Path) -> None:
    repo, head = _armed_release_root(tmp_path)
    git(repo, "config", "remote.origin.url", "https://peer.invalid/repository.git")
    git(repo, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
    git(repo, "update-ref", "refs/remotes/origin/dev", head)

    status = _status(repo)

    assert status["next_action"] == ""
    assert _through_the_hook(repo, "switch", "-c", "dev", "main").returncode != 0


def test_the_created_branch_goes_on_as_an_accepted_root_does_today(tmp_path: Path) -> None:
    """After the creation status names the candidate bootstrap, as for a branch made by hand."""
    repo, _head = _armed_release_root(tmp_path)
    assert _through_the_hook(repo, "switch", "-c", "dev", "main").returncode == 0

    status = _status(repo)

    assert status["required_gaps"] == ["candidate_branch_missing"]
    assert status["next"]["argv"][:3] == ["ethos", "lane", "candidate"]


def test_status_names_no_creation_where_no_policy_governs_the_head(tmp_path: Path) -> None:
    """A release head without a release binding and without a valid profile has no policy."""
    repo, head = _armed_release_root(tmp_path)
    bare = git(repo, "commit-tree", git(repo, "mktree"), "-p", head, "-m", "nothing governs")
    git(repo, "update-ref", "refs/heads/main", bare)
    git(repo, "reset", "-q", "--hard", bare)

    named = str(_status(repo)["next_action"])
    done = _through_the_hook(repo, "branch", "dev", "main")

    assert "git switch -c" not in named
    assert done.returncode != 0
    assert _gaps(done) == ["ref_move_policy_unavailable"]


def test_a_linked_checkout_at_the_release_head_creates_the_branch(tmp_path: Path) -> None:
    """Git names a linked checkout's own directory in `GIT_DIR` and sets no `GIT_COMMON_DIR`."""
    repo, head = _armed_release_root(tmp_path)
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "-q", "--detach", linked.as_posix(), "main")

    done = _through_the_hook(linked, "switch", "-c", "dev", "main")

    assert done.returncode == 0, done.stderr
    assert git(repo, "rev-parse", "refs/heads/dev") == head


def test_a_move_in_another_repository_is_not_judged_by_this_one(tmp_path: Path) -> None:
    """A checkout that lacks the branch admits no move that Git prepares in another repository."""
    repo, head = _armed_release_root(tmp_path)
    own = git(repo, "commit-tree", f"{head}^{{tree}}", "-m", "the accepted branch's own")
    git(repo, "update-ref", "refs/heads/dev", own)
    twin = tmp_path / "twin"
    git(repo, "clone", "-q", "--branch", "main", repo.as_posix(), twin.as_posix())
    git(twin, "remote", "remove", "origin")

    done = run_command(
        twin,
        ("git", f"--git-dir={repo / '.git'}", "update-ref", "refs/heads/dev", head),
        timeout=60,
    )

    assert done.returncode != 0
    assert git(repo, "rev-parse", "refs/heads/dev") == own


def test_a_creation_with_git_common_dir_set_is_not_admitted(tmp_path: Path) -> None:
    """The variable's presence refuses, even when it names the checkout's own common directory."""
    repo, _head = _armed_release_root(tmp_path)

    done = run_command(
        repo,
        ("git", "branch", "dev", "main"),
        timeout=60,
        env={"GIT_COMMON_DIR": (repo / ".git").as_posix()},
    )

    assert done.returncode != 0
    assert _gaps(done) == _REFUSAL
    assert git(repo, "branch", "--list", "dev") == ""


def test_a_creation_judged_by_another_repository_s_hooks_is_not_admitted(tmp_path: Path) -> None:
    """Git runs the hooks of `GIT_COMMON_DIR`; neither repository is admitted from the other's."""
    repo, head = _armed_release_root(tmp_path)
    own = git(repo, "commit-tree", f"{head}^{{tree}}", "-m", "the accepted branch's own")
    git(repo, "update-ref", "refs/heads/dev", own)
    twin = tmp_path / "twin"
    git(repo, "clone", "-q", "--branch", "main", repo.as_posix(), twin.as_posix())
    git(twin, "remote", "remove", "origin")
    assert install_fixture_hook_runtime(twin)["current"]

    done = run_command(
        twin,
        ("git", "update-ref", "refs/heads/dev", head),
        timeout=60,
        env={"GIT_DIR": (twin / ".git").as_posix(), "GIT_COMMON_DIR": (repo / ".git").as_posix()},
    )

    assert done.returncode != 0
    assert _gaps(done) == _REFUSAL
    assert git(repo, "rev-parse", "refs/heads/dev") == own
