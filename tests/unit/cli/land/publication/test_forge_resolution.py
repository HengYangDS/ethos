"""A peer's forge web repository resolves from local connection metadata only."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.publication.forge import forge_web_repository
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

_FOLLOW_UP = "git config --local remote.gitlab.forgeRepository <web-url>"


def _peer(tmp_path: Path, url: str | None, *, key: str | None = None) -> Path:
    """Create one repository whose `gitlab` remote and local key are exactly as given."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "dev")
    if url is not None:
        git(repo, "remote", "add", "gitlab", url)
    if key is not None:
        git(repo, "config", "--local", "remote.gitlab.forgeRepository", key)
    return repo


def test_the_local_key_wins_over_the_git_remote(tmp_path: Path) -> None:
    """The key is used exactly as written, before any remote transport."""
    key = "http://forge.test:8080/team/repo.git"
    repo = _peer(tmp_path, "https://other.test/team/repo.git", key=key)
    resolved = forge_web_repository(repo, "gitlab")
    assert (resolved.url, resolved.gap, resolved.next_action) == (key, "", "")


@pytest.mark.parametrize(
    "key",
    ["https://oauth2:s3cret@example.test/team/repo", "forge.test/team/repo", "https://f.test/r"],
)
def test_an_invalid_local_key_refuses_without_echo_or_fallback(tmp_path: Path, key: str) -> None:
    """A present key is authoritative: an invalid one never falls back to a valid remote."""
    repo = _peer(tmp_path, "https://forge.test/team/repo.git", key=key)
    resolved = forge_web_repository(repo, "gitlab")
    assert (resolved.url, resolved.gap) == ("", "forge_repository_invalid:gitlab")
    assert resolved.next_action == _FOLLOW_UP
    assert key not in repr(resolved)


@pytest.mark.parametrize(
    ("url", "wanted"),
    [
        ("https://forge.test/team/repo.git", "https://forge.test/team/repo"),
        ("http://forge.test:8080/team/repo.git/", "http://forge.test:8080/team/repo"),
        ("https://forge.test/group/sub/repo/", "https://forge.test/group/sub/repo"),
    ],
)
def test_an_http_remote_keeps_scheme_host_and_port(tmp_path: Path, url: str, wanted: str) -> None:
    """One trailing slash and one `.git` suffix go; everything else stays."""
    resolved = forge_web_repository(_peer(tmp_path, url), "gitlab")
    assert (resolved.url, resolved.gap, resolved.next_action) == (wanted, "", "")


def test_an_instead_of_rewrite_is_honored(tmp_path: Path) -> None:
    """Git's own URL rewriting decides the remote, as every Git command sees it."""
    repo = _peer(tmp_path, "gl:team/repo.git")
    git(repo, "config", "--local", "url.https://forge.test/.insteadOf", "gl:")
    assert forge_web_repository(repo, "gitlab").url == "https://forge.test/team/repo"


def test_a_credentialed_remote_refuses_without_echo(tmp_path: Path) -> None:
    """Userinfo is never copied into a gap, an action or a URL."""
    url = "https://oauth2:t0ken@example.test/team/repo.git"
    resolved = forge_web_repository(_peer(tmp_path, url), "gitlab")
    assert (resolved.url, resolved.gap) == ("", "forge_repository_credentialed:gitlab")
    assert resolved.next_action == _FOLLOW_UP
    assert "t0ken" not in repr(resolved)


@pytest.mark.parametrize(
    "url",
    [
        "ssh://git@example.test:2222/team/repo.git",
        "git@example.test:team/repo.git",
        "https://forge.test/repo.git",
        None,
    ],
)
def test_an_unresolved_peer_names_the_local_follow_up(tmp_path: Path, url: str | None) -> None:
    """SSH, scp-like, single-segment and missing remotes stay unresolved with one action."""
    resolved = forge_web_repository(_peer(tmp_path, url), "gitlab")
    assert (resolved.url, resolved.gap) == ("", "forge_repository_unresolved:gitlab")
    assert resolved.next_action == _FOLLOW_UP
