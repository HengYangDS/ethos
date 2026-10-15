"""Hosted observation records the host peer's remote without assuming its name."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import tools.ci.hosted_observation as hosted_observation
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_publication_topology

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_dry_run_records_the_host_peer_remote_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_publication_topology(repo, gitlab_remote="gitlab", host_provider="gitlab")
    git(repo, "remote", "add", "origin", "https://origin.example.invalid/ethos.git")
    git(repo, "remote", "add", "gitlab", "https://gitlab.example.invalid/ethos.git")
    config = repo / ".config/checks/hosted-observation/policy.toml"
    config.parent.mkdir(parents=True)
    config.write_text('output = "observation.json"\nproviders = []\n', encoding="utf-8")
    monkeypatch.setattr(hosted_observation, "ROOT", repo)
    monkeypatch.setattr(hosted_observation, "CONFIG", config)

    assert hosted_observation.capture_observation() == 1

    payload = json.loads((repo / "observation.json").read_text(encoding="utf-8"))
    assert payload["remote_url"] == "https://gitlab.example.invalid/ethos.git"
