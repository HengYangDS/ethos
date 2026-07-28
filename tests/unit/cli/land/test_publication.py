from __future__ import annotations

from pathlib import Path

import pytest

from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.domain.land.publication import local_ci_owner_scripts
from ethos.domain.land.publication import local_proposal_package
from ethos.domain.land.publication import publication_readiness
from ethos.domain.land.publication import publication_with_remote_matrix
from ethos.domain.land.publication import remote_publication_deferred
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.contract_helpers import write_role_policy
from tests.support.ethos_cli_runner import run_ethos


def test_publish_reports_invalid_local_ci_fallback_evidence_manifest(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{not-json", encoding="utf-8")

    payload = run_ethos("publish", "--json", cwd=repo)

    evidence_status = payload["data"]["local_ci_fallback"]["evidence_status"]
    assert evidence_status == {
        "state": "invalid",
        "path": "build/evidence/local-ci/fallback.json",
        "current_head": head,
        "evidence_head": "",
        "ok": False,
        "next_action": (
            "rerun tools/ci/scripts/run-local-ci.sh to refresh local fallback evidence"
        ),
    }


def test_publish_reports_local_readiness_without_remote_push() -> None:
    payload = run_ethos("publish", "--json")
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"
    proposal_branch = load_branch_role_policy(Path.cwd()).proposal_branch_for_source(branch)

    assert payload["summary"]["remote_push"] == "not_performed"
    assert (
        payload["data"]["local_ci_fallback"] == payload["data"]["publication"]["fallback_evidence"]
    )
    assert payload["data"]["local_ci_fallback"]["owner_scripts"] == local_ci_owner_scripts(
        root=Path.cwd()
    )

    publication = payload["data"]["publication"]
    assert publication["proposal_branch"] == proposal_branch
    assert publication["local_proposal_package"]["source_branch"] == branch
    assert publication["local_proposal_package"]["proposal_branch"] == proposal_branch
    assert (
        "run local-ci fallback when remote publication is unavailable"
        in publication["local_proposal_package"]["required_steps"]
    )
    assert payload["next_actions"]


def test_publish_observes_gitlab_and_github_independently_without_push(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    gitlab = tmp_path / "gitlab.git"
    github = tmp_path / "github.git"
    for remote in (gitlab, github):
        git(tmp_path, "init", "--bare", remote.as_posix())
    git(repo, "remote", "add", "origin", gitlab.as_posix())
    git(repo, "remote", "add", "github", github.as_posix())
    git(repo, "push", "--set-upstream", "origin", "dev")
    git(repo, "push", "--set-upstream", "github", "dev")

    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["summary"]["hosted_ci_status_claimed"] is False
    observations = payload["data"]["remote_observations"]
    assert set(observations) == {"gitlab", "github"}
    assert observations["gitlab"]["availability"]["remote"] == "origin"
    assert observations["github"]["availability"]["remote"] == "github"
    assert payload["data"]["publication"]["remote_observations"] == observations


def test_publish_reports_synchronized_tracking_without_claiming_a_push(
    tmp_path: Path,
) -> None:
    """A matching tracking ref is an observation, not an executed publication."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    remote = tmp_path / "origin.git"
    for root, *args in (
        (tmp_path, "init", "--bare", remote.as_posix()),
        (repo, "remote", "add", "origin", remote.as_posix()),
        (repo, "push", "--set-upstream", "origin", "dev"),
    ):
        git(root, *args)

    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert {
        "remote_sync_state": payload["summary"]["remote_sync_state"],
        "remote_publication_state": payload["summary"]["remote_publication_state"],
        "remote_push": payload["summary"]["remote_push"],
        "remote_state": payload["data"]["publication"]["remote_state"],
    } == {
        "remote_sync_state": "synchronized",
        "remote_publication_state": "synchronized",
        "remote_push": "not_performed",
        "remote_state": "synchronized",
    }
    assert (
        payload["data"]["publication"]["remote_observations"]["gitlab"]["sync"]["state"]
        == "synchronized"
    )
    assert payload["data"]["publication"]["remote_push"] == "not_performed"
    assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"


def test_publication_readiness_uses_local_fallback_when_fallback_omits_evidence_status() -> None:
    policy = load_branch_role_policy(Path.cwd())
    for evidence_status in ({}, None):
        publication = publication_readiness(
            branch="dev",
            local_ok=True,
            policy=policy,
            local_ci_fallback={"evidence_status": evidence_status},
        )

        assert publication["next_actions"] == [
            "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"
        ]


def test_publish_uses_configured_proposal_branch_role_policy(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["local_proposal_package"]["source_branch"] == "lane/topic"
    assert publication["local_proposal_package"]["proposal_branch"] == "review/topic"


@pytest.mark.parametrize(
    ("availability", "expected_reason"),
    [
        (
            {"state": "unavailable", "available": False},
            "remote unavailable; use local-ci fallback evidence",
        ),
        (
            {"state": "available", "available": True},
            "remote publication adapter unavailable",
        ),
    ],
    ids=("unavailable", "available"),
)
def test_remote_publication_deferred_preserves_local_only_boundary(
    availability: dict[str, object], expected_reason: str
) -> None:
    deferred = remote_publication_deferred(availability)

    assert deferred["remote_push"] == "not_performed"
    assert deferred["state"] == "deferred"
    assert deferred["reason"] == expected_reason
    assert deferred["availability"] == availability
    assert deferred["fallback"]["hosted_ci_status_claimed"] is False


def test_local_proposal_package_uses_safe_fallback_and_reconciliation_only_when_needed() -> None:
    proposal = local_proposal_package(branch="lane/topic", proposal_branch="review/topic")

    assert proposal["remote_availability"]["state"] == "not_probed"
    assert proposal["local_ci_fallback"]["evidence_status"]["state"] == "not_checked"
    assert (
        publication_with_remote_matrix(
            proposal, {"state": "reconciliation_required"}, remote_available=False
        )
        == proposal
    )
    assert publication_with_remote_matrix(
        proposal, {"state": "reconciliation_required"}, remote_available=True
    )["next_actions"] == ["reconcile diverged remotes before creating a proposal branch"]
