"""Provider-specific review observations cannot fabricate deletion authority."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.publication.retirement as retirement
from tests.support.governed_repository import git
from tests.unit.cli.land.publication.support import PROPOSAL_REF
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
    git(repo, "remote", "set-url", "gitlab", target)
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
        assert command[command.index("--repo") + 1] == target.removesuffix(".git")
        assert branch in command
        assert kwargs["stdin"] == ""
        assert kwargs["timeout"] == 60
        assert kwargs["env"]["GH_PROMPT_DISABLED"] == "1"
        assert kwargs["env"]["GLAB_NO_PROMPT"] == "1"
        if case == "timeout":
            raise subprocess.TimeoutExpired(command, 30)
        return subprocess.CompletedProcess(command, 1 if case == "denied" else 0, output, "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    result = retirement.observe_proposal_review(repo, "gitlab", provider, branch)

    assert result["verdict"] == wanted
    assert result["state"] == {"pass": "closed", "block": "open", "unknown": "unavailable"}[wanted]


def test_review_endpoint_is_explicit_when_git_transport_cannot_identify_the_api(tmp_path: Path):
    """An SSH port or alias cannot silently become a Forge API endpoint."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    git(repo, "remote", "set-url", "gitlab", "ssh://git@example.test:2222/team/repo.git")
    result = retirement.observe_proposal_review(
        repo, "gitlab", "gitlab", PROPOSAL_REF.removeprefix("refs/heads/")
    )
    assert result["verdict"] == "unknown"
    assert result["reason"] == "forge_repository_unresolved:gitlab"
    assert result["next_action"] == "git config --local remote.gitlab.forgeRepository <web-url>"


def test_an_http_remote_reaches_the_native_client_with_its_port(tmp_path: Path, monkeypatch):
    """The remote's scheme and port become the client's host; `.git` is not part of it."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    target = "http://forge.test:8080/team/repo"
    git(repo, "remote", "set-url", "gitlab", f"{target}.git")
    native = retirement.process.run_command

    def provider_process(root, command, **kwargs):
        if command[0] != "glab":
            return native(root, command, **kwargs)
        assert command[command.index("--repo") + 1] == target
        assert kwargs["env"]["GITLAB_HOST"] == "http://forge.test:8080"
        return subprocess.CompletedProcess(command, 0, "[]", "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    result = retirement.observe_proposal_review(repo, "gitlab", "gitlab", "proposal/finished")
    assert result["verdict"] == "pass"
    assert result["state"] == "closed"


def test_local_remote_api_locator_does_not_need_a_tracked_private_address(
    tmp_path: Path, monkeypatch
):
    """Local connection metadata feeds the native client without becoming repository policy."""
    repo, _peers, _proposal, _accepted = retirement_fixture(tmp_path)
    target = "http://forge.example:8443/team/repo"
    git(repo, "config", "--local", "remote.gitlab.forgeRepository", target)
    native = retirement.process.run_command

    def provider_process(root, command, **kwargs):
        if command[0] != "glab":
            return native(root, command, **kwargs)
        assert command[command.index("--repo") + 1] == target
        assert kwargs["env"]["GITLAB_HOST"] == "http://forge.example:8443"
        return subprocess.CompletedProcess(command, 0, "[]", "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    result = retirement.observe_proposal_review(repo, "gitlab", "gitlab", "proposal/finished")
    assert result["verdict"] == "pass"
    assert result["state"] == "closed"
