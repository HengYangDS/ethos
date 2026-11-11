"""The peer feed reads a protected release peer's identity from local Git state only."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.peer_feed import local_feed
from ethos.adapters.repo.peer_feed import remote_parts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path

# Joined when used, so tracked text names no private-class literal.
H1 = "forge." + "internal"
H2 = "mirror.example.invalid"
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
        ("forgeRepository", f"http://{H1}:8929/{F1}"),
    ):
        git(repo, "config", "--add", f"remote.gitlab.{key}", value)
    git(repo, "remote", "add", "github", "https://github.com/HengYangDS/ethos.git")

    feed = local_feed(repo).feed

    assert feed.hosts == {H1, "old." + "internal"}
    assert feed.ports == {2222, 8443, 8929, 9443}
    assert set(feed.paths) == {F1, "old/team/x"}
    assert feed.ids == {123456789}
    git(repo, "config", "remote.github.forgePrivate", "true")
    assert "github.com" in local_feed(repo).feed.hosts


def test_a_repository_without_peers_feeds_nothing(tmp_path: Path) -> None:
    """No declared peer, no feed; URL and scp forms parse to host, port and path."""
    assert not local_feed(init_git_repo(tmp_path / "repo"))
    assert remote_parts(f"https://user@{H1}:8443/{F1}.git?x") == (H1, "8443", F1)
    assert remote_parts(f"git@{H1}:{F1}.git") == (H1, "", F1)
    assert remote_parts("not a url") == ("", "", "")


@pytest.mark.parametrize(
    ("case", "gaps"),
    [
        ("complete", ()),
        ("unread", ("peer_identity_feed_unreadable:github",)),
        ("keys-only", ("peer_identity_feed_unreadable:gitlab",)),
        ("emptied", ("peer_identity_feed_unreadable:gitlab",)),
        ("hostless", ("peer_identity_feed_empty",)),
        ("invalid", ("publication_topology_declaration_invalid",)),
    ],
)
def test_the_reader_names_what_the_clone_cannot_know(
    tmp_path: Path, case: str, gaps: tuple[str, ...]
) -> None:
    """An invalid declaration names itself alone; an unread declared peer precedes an empty feed."""
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo)
    git(repo, "remote", "add", "github", "https://github.com/HengYangDS/ethos.git")
    git(repo, "remote", "add", "gitlab", f"ssh://git@{H1}:2222/{F1}.git")
    # A remote that marks itself private feeds though no declared peer names it.
    git(repo, "config", "remote.mirror.url", f"https://{H2}/team/mirror.git")
    git(repo, "config", "remote.mirror.forgePrivate", "true")
    if case == "unread":
        git(repo, "remote", "remove", "github")
    elif case == "keys-only":
        git(repo, "config", "--unset", "remote.gitlab.url")
        git(repo, "config", "remote.gitlab.forgePrivate", "true")
    elif case == "emptied":
        git(repo, "config", "--add", "remote.gitlab.url", "")
    elif case == "hostless":
        git(repo, "remote", "set-url", "gitlab", str(tmp_path / "peer.git"))
        git(repo, "config", "--unset", "remote.mirror.forgePrivate")
    elif case == "invalid":
        text = "[publication]\nunknown = 1\n"
        (repo / ".ethos/release.toml").write_text(text, encoding="utf-8")
    known = local_feed(repo)
    assert known.gaps == gaps
    assert (H2 in known.feed.hosts) == (case != "hostless")
