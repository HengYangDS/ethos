"""Local publication readiness and peer observations never imply a remote effect."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.domain.land.publication as publication_domain
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.domain.land.publication import local_ci_owner_scripts
from ethos.domain.land.publication import publication_readiness
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import write_role_policy


def _write_local_only_publication(repo: Path) -> None:
    release = repo / ".ethos" / "release.toml"
    release.write_text(
        "[publication]\n"
        'local_verification_command = "dev/verify"\n'
        'local_installation_command = "dev/install"\n',
        encoding="utf-8",
    )


def _publish_fixture(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    return repo, head


def test_publish_reports_local_readiness_without_remote_push() -> None:
    payload = run_ethos("publish", "--json")
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"

    assert payload["summary"]["remote_push"] == "not_performed"
    assert (
        payload["data"]["local_ci_fallback"] == payload["data"]["publication"]["fallback_evidence"]
    )
    fallback = payload["data"]["local_ci_fallback"]
    assert fallback["owner_scripts"] == local_ci_owner_scripts(
        root=Path.cwd(), command=fallback["command"]
    )

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == branch
    assert publication["source_role"] == load_branch_role_policy(Path.cwd()).role_for_branch(branch)
    assert "proposal_branch" not in publication
    assert "local_proposal_package" not in publication
    assert payload["next_action"]


@pytest.mark.parametrize("case", ["invalid", "custom", "retired"])
def test_publish_fallback_evidence_matrix(tmp_path: Path, case: str) -> None:
    repo, head = _publish_fixture(tmp_path)
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    command = "uv run --locked --no-sync nox -s full"
    if case == "custom":
        release = repo / ".ethos/release.toml"
        release.write_text(
            release.read_text().replace('"dev/verify"', f'"{command}"'), encoding="utf-8"
        )
        head = commit_fixture(repo, "declare canonical local verification")
        seed_executed_proof(repo, head)
    else:
        manifest.parent.mkdir(parents=True)
        content = (
            "{not-json"
            if case == "invalid"
            else (
                f'{{"command":"retired/verify","head":"{head}","required_gaps":[],"verdict":"pass"}}\n'
            )
        )
        manifest.write_text(content, encoding="utf-8")
    payload = run_ethos("publish", "--json", cwd=repo)
    evidence = payload["data"]["local_ci_fallback"]["evidence_status"]
    expected = {
        "invalid": ("invalid", "rerun dev/verify to refresh local fallback evidence"),
        "custom": ("missing", f"run {command} as local fallback evidence"),
        "retired": ("stale", "run dev/verify as local fallback evidence"),
    }[case]
    assert (evidence["state"], evidence["next_action"]) == expected
    if case == "custom":
        assert (payload["data"]["local_ci_fallback"]["command"], payload["next_action"]) == (
            command,
            f"run {command} as local fallback evidence",
        )


@pytest.mark.parametrize("mode", ["dual", "local", "single", "tracking"])
def test_publish_peer_topology_matrix(tmp_path: Path, mode: str) -> None:
    repo, head = _publish_fixture(tmp_path)
    if mode == "local":
        _write_local_only_publication(repo)
        head = commit_fixture(repo, "declare local-only publication")
        seed_executed_proof(repo, head)
    else:
        if mode == "single":
            release = repo / ".ethos/release.toml"
            parts = release.read_text().split("[[publication.peers]]", 2)
            release.write_text(parts[0] + "[[publication.peers]]" + parts[1])
            head = commit_fixture(repo, "declare GitLab-only publication")
            seed_executed_proof(repo, head)
        peers = (
            (("gitlab", "origin"), ("github", "github"))
            if mode == "dual"
            else (("gitlab", "origin"),)
        )
        for peer, remote in peers:
            target = tmp_path / f"{peer}.git"
            git(tmp_path, "init", "--bare", target.as_posix())
            git(repo, "remote", "add", remote, target.as_posix())
            git(repo, "push", "--set-upstream", remote, "dev")
    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)
    if mode == "local":
        assert payload["verdict"] == "pass"
        return
    observations = payload["data"]["remote_observations"]
    assert set(observations) == (
        {"gitlab", "github"} if mode in {"dual", "tracking"} else {"gitlab"}
    )
    assert payload["summary"]["remote_push"] == "not_performed"
    if mode == "dual":
        assert observations["github"]["availability"]["remote"] == "github"
        assert not {"remote_availability", "remote_sync"} & set(payload["data"])
    elif mode == "single":
        assert payload["data"]["remote_topology"]["state"] == "ready"
    else:
        assert payload["summary"]["remote_sync_states"] == {
            "gitlab": "synchronized",
            "github": "remote_tracking_missing",
        }
        assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"


def test_publication_readiness_uses_local_fallback_when_fallback_omits_evidence_status() -> None:
    policy = load_branch_role_policy(Path.cwd())
    command = "dev/verify"
    for evidence_status in ({}, None):
        publication = publication_readiness(
            branch="dev",
            local_ok=True,
            policy=policy,
            local_ci_fallback={"evidence_status": evidence_status},
            local_verification_command=command,
        )

        assert publication["next_action"] == f"run {command} as local fallback evidence"


def test_publish_local_readiness_does_not_project_a_publication_plan(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == "lane/topic"
    assert publication["source_role"] == "work_lane"
    assert "proposal_branch" not in publication
    assert "local_proposal_package" not in publication
    context = publication_domain.observe_publication(
        repo, apply=False, authorized=False, expect_head=None, target_refs=()
    )
    observed = publication_domain.publication_readiness_result(
        context, apply=False, authorized=False, expect_head=None, probe_remote=False
    )
    assert observed.model_dump(mode="json")["data"] == payload["data"]
    assert observed.state == payload["state"]
