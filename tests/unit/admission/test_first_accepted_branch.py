"""The first accepted branch is one shape: created at the release head, from nothing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.ref_move_policy import first_accepted_branch
from ethos.adapters.admission.ref_move_policy import first_accepted_branch_step
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_ACCEPTED = "refs/heads/dev"
_FETCH_ALL = "+refs/heads/*:refs/remotes/{remote}/*"


def _only_main(repo: Path) -> str:
    git(repo, "branch", "-M", "main")
    assert git(repo, "for-each-ref", "--format=%(refname)", "refs/heads") == "refs/heads/main"
    return git(repo, "rev-parse", "HEAD")


def _release_root(tmp_path: Path, object_format: str = "sha1") -> tuple[Path, str]:
    """A repository whose only branch is its release branch, checked out and clean."""
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    write_test_profile(repo)
    commit_fixture(repo, "chore: declare the repository profile")
    return repo, _only_main(repo)


def _holds(repo: Path, head: str, ref_name: str = _ACCEPTED) -> bool:
    return first_accepted_branch(repo, BranchRolePolicy(), ref_name, "0" * len(head), head)


def _remote(repo: Path, name: str, *refspecs: str) -> None:
    git(repo, "config", f"remote.{name}.url", "https://peer.invalid/repository.git")
    for refspec in refspecs:
        git(repo, "config", "--add", f"remote.{name}.fetch", refspec.format(remote=name))


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_the_creation_at_the_release_head_holds(tmp_path: Path, object_format: str) -> None:
    repo, head = _release_root(tmp_path, object_format)

    assert _holds(repo, head)


def test_an_old_value_that_is_not_a_zero_object_name_is_not_asked(tmp_path: Path) -> None:
    repo, head = _release_root(tmp_path)

    assert not first_accepted_branch(repo, BranchRolePolicy(), _ACCEPTED, "0" * 39, head)


def test_a_branch_that_exists_is_not_created(tmp_path: Path) -> None:
    """Git gives a forced move a zero old value, as it gives a creation; the ref store tells."""
    repo, head = _release_root(tmp_path)
    earlier = git(repo, "commit-tree", f"{head}^{{tree}}", "-m", "the accepted branch's own")
    git(repo, "update-ref", _ACCEPTED, earlier)

    assert not _holds(repo, head)


def _another_commit(repo: Path, head: str) -> str:
    return git(repo, "commit-tree", f"{head}^{{tree}}", "-p", head, "-m", "not the release head")


def _detach_elsewhere(repo: Path, head: str) -> str:
    git(repo, "checkout", "-q", "--detach", _another_commit(repo, head))
    return head


def _ask_for_the_checked_out_commit(repo: Path, head: str) -> str:
    """The checkout is at the asked commit, and the release branch is not."""
    other = _another_commit(repo, head)
    git(repo, "checkout", "-q", "--detach", other)
    return other


def _stage_a_change(repo: Path, head: str) -> str:
    (repo / "staged").write_text("staged\n", encoding="utf-8")
    git(repo, "add", "staged")
    return head


def _leave_an_untracked_file(repo: Path, head: str) -> str:
    (repo / "untracked").write_text("untracked\n", encoding="utf-8")
    return head


def _create_the_candidate(repo: Path, head: str) -> str:
    git(repo, "update-ref", "refs/heads/candidate/dev", head)
    return head


def _peer_holds_it(repo: Path, head: str) -> str:
    _remote(repo, "origin", _FETCH_ALL)
    git(repo, "update-ref", "refs/remotes/origin/dev", head)
    return head


def _second_peer_holds_it(repo: Path, head: str) -> str:
    _remote(repo, "origin", _FETCH_ALL)
    _remote(repo, "mirror", _FETCH_ALL)
    git(repo, "update-ref", "refs/remotes/mirror/dev", head)
    return head


def _refspecs(*refspecs: str) -> Callable[[Path, str], str]:
    def change(repo: Path, head: str) -> str:
        _remote(repo, "origin", *refspecs)
        return head

    return change


def _configuration_that_git_cannot_list(repo: Path, head: str) -> str:
    _remote(repo, "origin", _FETCH_ALL, "refs/heads/*:refs/peers/origin/dev")
    git(repo, "update-ref", "refs/remotes/origin/dev", head)
    return head


_REFUSED = {
    "another commit": _another_commit,
    "the checkout is elsewhere": _detach_elsewhere,
    "the checked-out commit is not the release head": _ask_for_the_checked_out_commit,
    "a staged change": _stage_a_change,
    "an untracked file": _leave_an_untracked_file,
    "a candidate branch": _create_the_candidate,
    "a peer holds it": _peer_holds_it,
    "a second peer holds it": _second_peer_holds_it,
    "a configuration that Git cannot list": _configuration_that_git_cannot_list,
    "a clone of one branch": _refspecs("+refs/heads/main:refs/remotes/origin/main"),
    "a remote without a fetch refspec": _refspecs(),
    "the default without its force mark": _refspecs("refs/heads/*:refs/remotes/origin/*"),
    "another layout": _refspecs("+refs/heads/*:refs/peers/origin/heads/*"),
    "a second refspec": _refspecs(_FETCH_ALL, "+refs/tags/*:refs/tags/*"),
    "a negative refspec": _refspecs(_FETCH_ALL, "^refs/heads/wip/*"),
    "an empty refspec": _refspecs(_FETCH_ALL, ""),
}


@pytest.mark.parametrize("change", _REFUSED)
def test_one_change_to_the_shape_refuses_it(tmp_path: Path, change: str) -> None:
    """Each case differs from the admitted one by exactly the change that it names."""
    repo, head = _release_root(tmp_path)
    assert _holds(repo, head)

    asked = _REFUSED[change](repo, head)

    assert not _holds(repo, asked)


def test_remotes_with_the_default_refspec_that_have_not_shown_the_branch_admit(
    tmp_path: Path,
) -> None:
    repo, head = _release_root(tmp_path)
    _remote(repo, "origin", _FETCH_ALL)
    _remote(repo, "mirror", _FETCH_ALL)
    git(repo, "update-ref", "refs/remotes/origin/main", head)

    assert _holds(repo, head)


@pytest.mark.parametrize("ref_name", ["refs/heads/dev2", "refs/tags/dev", "refs/heads/main"])
def test_no_other_ref_is_the_first_accepted_branch(tmp_path: Path, ref_name: str) -> None:
    repo, head = _release_root(tmp_path)

    assert not _holds(repo, head, ref_name)


def test_a_linked_checkout_at_the_release_head_may_ask(tmp_path: Path) -> None:
    repo, head = _release_root(tmp_path)
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", "-q", "--detach", linked.as_posix(), head)

    assert _holds(linked, head)


def test_a_move_from_a_value_is_not_asked(tmp_path: Path) -> None:
    repo, head = _release_root(tmp_path)

    assert not first_accepted_branch(repo, BranchRolePolicy(), _ACCEPTED, head, head)


def test_a_release_binding_that_cannot_be_read_governs_nothing(tmp_path: Path) -> None:
    repo, _head = _release_root(tmp_path)
    head = commit_fixture_file(
        repo, ".ethos/release.toml", "[release\n", "chore: break the binding"
    )

    assert not _holds(repo, head)


def test_a_head_without_a_profile_governs_nothing(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    assert not _holds(repo, _only_main(repo))


def test_the_step_names_the_creation_it_would_admit(tmp_path: Path) -> None:
    repo, head = _release_root(tmp_path)
    policy = BranchRolePolicy()

    step = first_accepted_branch_step(repo, head)

    assert step.startswith("create the accepted branch at the release head")
    assert step.endswith(f"git switch -c {policy.accepted_branch} {policy.release_branch}")


def test_the_step_fetches_first_where_a_remote_is_configured(tmp_path: Path) -> None:
    repo, head = _release_root(tmp_path)
    _remote(repo, "origin", _FETCH_ALL)

    assert first_accepted_branch_step(repo, head).startswith("fetch every remote, then ")


def test_no_step_where_the_creation_is_refused(tmp_path: Path) -> None:
    repo, head = _release_root(tmp_path)
    git(repo, "update-ref", _ACCEPTED, head)

    assert first_accepted_branch_step(repo, head) == ""


def test_no_step_where_no_policy_governs_the_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")

    assert first_accepted_branch_step(repo, _only_main(repo)) == ""
