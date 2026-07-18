from __future__ import annotations

from pathlib import Path

from ethos.domain.land.publication import local_ci_owner_scripts
from ethos.domain.land.publication import publication_readiness
from ethos_core.contracts.branch.roles import load_branch_role_policy
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import write_role_policy


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
    submit_branch = load_branch_role_policy(Path.cwd()).submit_branch_for_source(branch)

    assert payload["summary"]["remote_push"] == "not_performed"
    assert (
        payload["data"]["local_ci_fallback"] == payload["data"]["publication"]["fallback_evidence"]
    )
    assert payload["data"]["local_ci_fallback"]["owner_scripts"] == local_ci_owner_scripts(
        root=Path.cwd()
    )

    publication = payload["data"]["publication"]
    assert publication["submit_branch"] == submit_branch
    assert publication["local_submit_package"]["source_branch"] == branch
    assert publication["local_submit_package"]["submit_branch"] == submit_branch
    assert (
        "run local-ci fallback when remote publication is unavailable"
        in publication["local_submit_package"]["required_steps"]
    )
    assert payload["next_actions"]


def test_publish_reports_remote_tracking_sync_state(monkeypatch) -> None:
    import ethos.surface.cli.root.lifecycle as lifecycle_cli  # noqa: PLC0415, RUF100 - local import isolates import-time state for this test

    local_head = "a" * 40
    remote_head = "b" * 40

    monkeypatch.setattr(lifecycle_cli.git, "current_head", lambda _repo: local_head)
    monkeypatch.setattr(
        lifecycle_cli.git,
        "remote_availability",
        lambda _repo: {
            "kind": "git_remote_availability",
            "remote": "origin",
            "state": "available",
            "available": True,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
        },
    )
    monkeypatch.setattr(
        lifecycle_cli.git,
        "remote_tracking_sync",
        lambda _repo, branch, remote="origin": {
            "kind": "git_remote_tracking_sync",
            "remote": remote,
            "branch": branch,
            "remote_ref": f"{remote}/{branch}",
            "state": "local_ahead",
            "local_head": local_head,
            "remote_head": remote_head,
            "ahead": 2,
            "behind": 0,
            "available": True,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [f"remote_tracking_local_ahead:{remote}/{branch}:2"],
        },
    )
    payload = run_ethos("publish", "--probe-remote", "--json")

    assert payload["summary"]["remote_sync_state"] == "local_ahead"
    sync = payload["data"]["remote_sync"]
    assert sync == payload["data"]["publication"]["remote_sync"]
    assert sync["local_head"] == local_head
    assert sync["remote_head"] == remote_head
    assert "remote_tracking_local_ahead" in sync["advisory_gaps"][0]


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
        payload["next_actions"][0] == "remote tracking ref is synchronized; no push was performed"
    )
    assert payload["data"]["mutation"]["decision"]["verdict"] == "defer"


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


def test_publish_does_not_probe_remote_without_explicit_flag(monkeypatch) -> None:
    import ethos.surface.cli.root.lifecycle as lifecycle_cli  # noqa: PLC0415, RUF100 - local import isolates command dependencies

    def unexpected_probe(_repo: Path) -> dict[str, object]:
        message = "publish must not probe a remote without --probe-remote"
        raise AssertionError(message)

    monkeypatch.setattr(lifecycle_cli.git, "remote_availability", unexpected_probe)
    monkeypatch.setattr(
        lifecycle_cli.git,
        "remote_availability_not_probed",
        lambda _repo: {
            "kind": "git_remote_availability",
            "remote": "origin",
            "state": "not_probed",
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
        },
    )

    payload = run_ethos("publish", "--json")

    assert payload["data"]["remote_availability"]["state"] == "not_probed"


def test_publish_uses_configured_submit_branch_role_policy(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["local_submit_package"]["source_branch"] == "lane/topic"
    assert publication["local_submit_package"]["submit_branch"] == "review/topic"
