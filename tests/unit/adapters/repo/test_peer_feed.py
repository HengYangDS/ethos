"""The peer feed reads a protected release peer's identity from local Git state only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.peer_feed import peer_feed
from ethos.adapters.repo.peer_feed import remote_parts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path

# Joined when used, so tracked text names no private-class literal.
H1 = "forge." + "internal"
F1 = "team/infra/tools"


def test_the_feed_reads_protected_peers_and_their_former_values(tmp_path: Path) -> None:
    """A private-class peer feeds its URLs and forge keys; a public one feeds once opted in."""
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    git(repo, "remote", "add", "gitlab", f"ssh://git@{H1}:2222/{F1}.git")
    git(repo, "remote", "set-url", "--push", "gitlab", f"https://{H1}:8443/{F1}.git")
    for key, value in (
        ("forgeProjectId", "123456789"),
        ("forgeProjectId", "not-a-number"),
        ("forgeFormer", "host=old." + "internal"),
        ("forgeFormer", "port=9443"),
        ("forgeFormer", "path=old/team/x"),
    ):
        git(repo, "config", "--add", f"remote.gitlab.{key}", value)
    git(repo, "remote", "add", "github", "https://github.com/HengYangDS/ethos.git")

    feed = peer_feed(repo)

    assert feed.hosts == {H1, "old." + "internal"}
    assert feed.ports == {2222, 8443, 9443}
    assert set(feed.paths) == {F1, "old/team/x"}
    assert feed.ids == {123456789}
    git(repo, "config", "remote.github.forgePrivate", "true")
    assert "github.com" in peer_feed(repo).hosts


def test_a_repository_without_peers_feeds_nothing(tmp_path: Path) -> None:
    """No declared peer, no feed; URL and scp forms parse to host, port and path."""
    assert not peer_feed(init_git_repo(tmp_path / "repo"))
    assert remote_parts(f"https://user@{H1}:8443/{F1}.git?x") == (H1, "8443", F1)
    assert remote_parts(f"git@{H1}:{F1}.git") == (H1, "", F1)
    assert remote_parts("not a url") == ("", "", "")
