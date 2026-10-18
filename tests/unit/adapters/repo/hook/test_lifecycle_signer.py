"""Status reports the local signer of lifecycle commits, blocking only where ETHOS commits."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.repo.commit.creation import commit_signer_action
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import start_adopted_candidate
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.repo.hook.observation import CommitPolicyEnforcement


def _capability(repo: Path) -> tuple[dict[str, Any], CommitPolicyEnforcement]:
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    return projected, cast(
        "CommitPolicyEnforcement", projected["data"]["commit_policy_enforcement"]
    )


def test_lifecycle_role_requires_the_local_signer_of_commit_creation(tmp_path: Path) -> None:
    """The accepted root creates lifecycle commits, so it needs the signer they use."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    assert git_process(repo, "config", "--unset", "user.signingkey").returncode == 0

    projected, capability = _capability(repo)

    assert projected["data"]["role"] == "accepted_root"
    assert projected["verdict"] == "block"
    assert "git_effect_signing_key_invalid" in projected["required_gaps"]
    assert capability["state"] == "unready"
    assert capability["required_gaps"] == ["git_effect_signing_key_invalid"]
    assert capability["signature_trust"]["state"] == "configured"
    assert capability["lifecycle_signer"] == {
        "state": "unready",
        "required": True,
        "required_gaps": ["git_effect_signing_key_invalid"],
    }
    assert capability["next_action"] == commit_signer_action(repo, "git_effect_signing_key_invalid")
    assert capability["next_action"] == (
        f"git -C {shlex.quote(str(repo))} config --local user.signingkey <absolute-ssh-public-key>"
    )


def test_verifying_checkout_reports_a_missing_signer_without_blocking(tmp_path: Path) -> None:
    """A detached checkout creates no lifecycle commit, so its signer is reported only."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    detached = tmp_path / "repo-verify"
    assert git_process(repo, "worktree", "add", "--detach", str(detached), "dev").returncode == 0
    assert git_process(repo, "config", "--unset", "user.signingkey").returncode == 0

    projected, capability = _capability(detached)

    assert projected["data"]["role"] == "detached"
    assert "git_effect_signing_key_invalid" not in projected["required_gaps"]
    assert capability["state"] == "armed"
    assert capability["required_gaps"] == []
    assert capability["lifecycle_signer"] == {
        "state": "unready",
        "required": False,
        "required_gaps": ["git_effect_signing_key_invalid"],
    }
    assert capability["next_action"] == ""
