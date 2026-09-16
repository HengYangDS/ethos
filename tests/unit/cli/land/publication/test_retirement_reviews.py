"""Provider-specific review observations cannot fabricate deletion authority."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.publication.retirement as retirement
from ethos.repository.release.publication import publication_topology
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import git
from tests.unit.cli.land.publication.test_retirement import retirement_fixture

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("provider", ["github", "gitlab"])
@pytest.mark.parametrize(
    ("case", "wanted"),
    [
        ("closed", "pass"),
        ("open", "block"),
        ("wrong_branch", "unknown"),
        ("wrong_state", "unknown"),
        ("malformed", "unknown"),
        ("denied", "unknown"),
        ("timeout", "unknown"),
    ],
)
def test_review_observation_is_bound_and_does_not_default_unknown_to_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: str, case: str, wanted: str
):
    """Exercise parsing and disposition; replace only the external provider process."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    target = f"https://{provider}.example/team/repository.git"
    git(repo, "remote", "set-url", "origin", target)
    branch = PROPOSAL_REF.removeprefix("refs/heads/")
    key = "headRefName" if provider == "github" else "source_branch"
    row = {key: branch, "state": "OPEN" if provider == "github" else "opened"}
    if case == "wrong_branch":
        row[key] = "proposal/unrelated"
    if case == "wrong_state":
        row["state"] = "closed"
    output = "invalid" if case == "malformed" else json.dumps([] if case == "closed" else [row])
    native = retirement.process.run_command

    def provider_process(root, command, **kwargs):
        if command[0] not in {"gh", "glab"}:
            return native(root, command, **kwargs)
        # These preconditions establish that the fake result answers the real query.
        assert root == repo
        assert command[command.index("--repo") + 1] == target
        assert branch in command
        assert kwargs["stdin"] == ""
        assert kwargs["timeout"] == 30
        assert kwargs["env"]["GH_PROMPT_DISABLED"] == "1"
        assert kwargs["env"]["GLAB_NO_PROMPT"] == "1"
        if case == "timeout":
            raise subprocess.TimeoutExpired(command, 30)
        return subprocess.CompletedProcess(command, 1 if case == "denied" else 0, output, "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    result = retirement.observe_proposal_review(repo, "origin", provider, branch)

    assert result["verdict"] == wanted
    assert result["state"] == {"pass": "closed", "block": "open", "unknown": "unavailable"}[wanted]


def test_review_endpoint_is_explicit_when_git_transport_cannot_identify_the_api(tmp_path: Path):
    """An SSH port or alias cannot silently become a Forge API endpoint."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    git(repo, "remote", "set-url", "origin", "ssh://git@example.test:2222/team/repo.git")
    result = retirement.observe_proposal_review(
        repo, "origin", "gitlab", PROPOSAL_REF.removeprefix("refs/heads/")
    )
    assert result["verdict"] == "unknown"
    assert result["reason"] == "forge_repository_required"


@pytest.mark.parametrize(
    "target", ["http://forge.internal:18086/team/repo", "https://github.com/team/repo"]
)
def test_peer_declaration_carries_api_coordinates_without_rewriting_git_transport(
    tmp_path: Path, target: str
):
    """Keep distinct native API and Git endpoints within one existing peer owner."""
    peer = {
        "id": "review",
        "provider": "gitlab",
        "role": "collaboration",
        "git_remote": "origin",
        "capabilities": ["repository", "publication"],
        "forge_repository": target,
    }
    for name in ("verify", "install"):
        path = tmp_path / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
    topology = publication_topology(
        tmp_path,
        {
            "publication": {
                "local_verification_command": "verify",
                "local_installation_command": "install",
                "peers": [peer],
            }
        },
    )
    assert topology["required_gaps"] == []
    assert topology["remotes"][0]["forge_repository"] == target


def test_explicit_gitlab_api_endpoint_reaches_native_client(tmp_path: Path, monkeypatch):
    """The API scheme and port remain distinct from the SSH transport."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    target = "http://forge.internal:18086/team/repo"
    native = retirement.process.run_command

    def provider_process(root, command, **kwargs):
        if command[0] != "glab":
            return native(root, command, **kwargs)
        assert command[command.index("--repo") + 1] == target
        assert kwargs["env"]["GITLAB_HOST"] == "http://forge.internal:18086"
        return subprocess.CompletedProcess(command, 0, "[]", "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    result = retirement.observe_proposal_review(
        repo, "origin", "gitlab", "proposal/finished", repository=target
    )
    assert result["verdict"] == "pass"
    assert result["state"] == "closed"


def test_local_remote_api_locator_does_not_need_a_tracked_private_address(
    tmp_path: Path, monkeypatch
):
    """Local connection metadata feeds the native client without becoming repository policy."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    target = "http://forge.example:18086/team/repo"
    git(repo, "config", "--local", "remote.origin.forgeRepository", target)
    native = retirement.process.run_command

    def provider_process(root, command, **kwargs):
        if command[0] != "glab":
            return native(root, command, **kwargs)
        assert command[command.index("--repo") + 1] == target
        assert kwargs["env"]["GITLAB_HOST"] == "http://forge.example:18086"
        return subprocess.CompletedProcess(command, 0, "[]", "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    result = retirement.observe_proposal_review(repo, "origin", "gitlab", "proposal/finished")
    assert result["verdict"] == "pass"
    assert result["state"] == "closed"
