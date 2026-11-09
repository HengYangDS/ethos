"""Push admission evaluates the remote Git names and never assumes one."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.publication import push_admission_report
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path


def test_push_admission_without_a_remote_name_fails_closed(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo, gitlab_remote="gitlab")
    head = git(repo, "rev-parse", "HEAD")

    report = push_admission_report(
        root=repo, target_ref="refs/heads/proposal/topic", pushed_head=head, remote_head=head
    )

    assert report["verdict"] == "block"
    assert "publication_remote_name_missing" in cast("list[str]", report["required_gaps"])


def test_a_push_that_only_peer_identity_blocks_names_its_reason(tmp_path: Path) -> None:
    """A push that an unknown feed alone blocks is `peer_identity_refused`."""
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo, gitlab_remote="gitlab")
    (repo / ".ethos").mkdir(exist_ok=True)
    text = 'profile_id = "push-reason"\n\n[peer_identity]\nmode = "required"\n'
    (repo / ".ethos/profile.toml").write_text(text, encoding="utf-8")
    head = commit_fixture(repo, "require the peer identity check")
    git(repo, "remote", "add", "gitlab", str(tmp_path / "gitlab.git"))
    git(repo, "config", "remote.gitlab.forgePrivate", "true")

    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/proposal/topic",
        pushed_head=head,
        remote_head=head,
        remote_name="gitlab",
    )

    gaps = cast("list[str]", report["required_gaps"])
    assert "peer_identity_feed_unreadable:github" in gaps
    assert cast("dict[str, str]", report["decision"])["reason"] == "peer_identity_refused"
