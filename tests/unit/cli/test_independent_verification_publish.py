from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path


def _require_independent_publish_verification(repo: Path) -> None:
    profile = repo / ".ethos" / "profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8")
        + '\n[independent_verification.actions.publish]\nmode = "required"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/profile.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "require independent publish verification",
    )


def test_publish_remains_local_first_when_independent_verification_is_disabled(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)

    payload = run_ethos("publish", "--json", cwd=repo)

    assert payload["ok"] is True
    verification = payload["data"]["independent_verification"]
    assert verification["mode"] == "disabled"
    assert verification["evidence_class"] == "local_readiness"
    assert payload["summary"]["independent_verification"] == "local_readiness"


def test_publish_fails_closed_only_for_a_publish_policy_that_requires_receipt(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    _require_independent_publish_verification(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)

    payload = run_ethos("publish", "--json", cwd=repo)

    assert "independent_verification_receipt_required" in payload["required_gaps"]
    verification = payload["data"]["independent_verification"]
    assert verification["state"] == "blocked"
    assert verification["evidence_class"] == "local_readiness"
