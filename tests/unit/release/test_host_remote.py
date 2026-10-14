"""Resolve the host profile's Git remote from the declared publication peers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.release.configuration import host_git_remote
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("host", "github_provider", "expected"),
    [
        ("gitlab", "github", "gitlab"),
        ("github", "github", "github"),
        ("gitlab", "gitlab", ""),
        ("forgejo", "github", ""),
        ("", "github", ""),
    ],
    ids=("gitlab-host", "github-host", "ambiguous-host", "undeclared-host", "no-host-profile"),
)
def test_host_remote_is_the_sole_peer_on_the_host_provider(
    tmp_path: Path, host: str, github_provider: str, expected: str
) -> None:
    write_publication_topology(tmp_path, gitlab_remote="gitlab", host_provider=host)
    release = tmp_path / ".ethos/release.toml"
    release.write_text(
        release.read_text().replace('provider = "github"', f'provider = "{github_provider}"')
    )

    assert host_git_remote(tmp_path) == expected


@pytest.mark.parametrize("declaration", [None, "invalid\n"], ids=("undeclared", "invalid"))
def test_host_remote_is_empty_without_a_valid_release_declaration(
    tmp_path: Path, declaration: str | None
) -> None:
    if declaration is not None:
        (tmp_path / ".ethos").mkdir()
        (tmp_path / ".ethos/release.toml").write_text(declaration)

    assert host_git_remote(tmp_path) == ""
