"""Local publication readiness and peer observations never imply a remote effect."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import tomli_w

import ethos.domain.publication.inspection as publication_domain
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.domain.publication.inspection import local_ci_owner_scripts
from ethos.domain.publication.inspection import publication_readiness
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_role_policy
from tests.support.proof import seed_executed_proof


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
    release = repo / ".ethos/release.toml"
    declaration = tomllib.loads(release.read_text())
    default_command = declaration["publication"]["local_verification_command"]
    if case == "custom":
        declaration["publication"]["local_verification_command"] = command
        release.write_text(tomli_w.dumps(declaration), encoding="utf-8")
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
        "invalid": (
            "invalid",
            f"rerun {default_command} to refresh local fallback evidence",
        ),
        "custom": ("missing", f"run {command} as local fallback evidence"),
        "retired": ("stale", f"run {default_command} as local fallback evidence"),
    }[case]
    assert (evidence["state"], evidence["next_action"]) == expected
    if case == "custom":
        assert (payload["data"]["local_ci_fallback"]["command"], payload["next_action"]) == (
            command,
            f"run {command} as local fallback evidence",
        )


@pytest.mark.parametrize("probe_remote", [False, True])
@pytest.mark.parametrize("mode", ["dual", "local", "single", "tracking"])
def test_publish_peer_topology_matrix(tmp_path: Path, mode: str, *, probe_remote: bool) -> None:
    repo, head = _publish_fixture(tmp_path)
    peer_count = {"local": 0, "single": 1}.get(mode, 2)
    if peer_count < 2:
        release = repo / ".ethos/release.toml"
        sections = release.read_text().split("[[publication.peers]]")
        release.write_text("[[publication.peers]]".join(sections[: peer_count + 1]))
        head = commit_fixture(repo, f"declare {mode} publication")
        seed_executed_proof(repo, head)
    observed_peers = peer_count if mode == "dual" else min(peer_count, 1)
    peers = (("gitlab", "origin"), ("github", "github"))[:observed_peers]
    for peer, remote in peers:
        target = tmp_path / f"{peer}.git"
        git(tmp_path, "init", "--bare", target.as_posix())
        git(repo, "remote", "add", remote, target.as_posix())
        git(repo, "push", "--set-upstream", remote, "dev")
    args = ("--probe-remote",) if probe_remote else ()
    payload = run_ethos("publish", *args, "--json", cwd=repo)
    if mode == "local":
        assert payload["verdict"] == "pass"
        return
    if not probe_remote:
        expected = f"ethos publish --ref refs/heads/dev --probe-remote --expect-head {head} --json"
        assert payload["next_action"] == expected
    observations = payload["data"]["remote_observations"]
    expected_peers = {"gitlab", "github"} if mode in {"dual", "tracking"} else {"gitlab"}
    assert set(observations) == expected_peers
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


def test_publication_readiness_selects_fallback_or_admitted_proposal_observation() -> None:
    policy = load_branch_role_policy(Path.cwd())
    fallback = "run dev/verify as local fallback evidence"
    unprobed = {"gitlab": {"availability": {"state": "not_probed"}}}
    for branch, evidence_status, remotes, expected in (
        ("dev", {}, {}, fallback),
        ("dev", None, {}, fallback),
        (policy.work_branch("topic"), None, unprobed, "refs/heads/proposal/topic"),
        (policy.candidate_branch, None, unprobed, "select an admitted publication target ref"),
    ):
        publication = publication_readiness(
            branch=branch,
            head="a" * 40,
            local_ok=True,
            policy=policy,
            local_ci_fallback={"evidence_status": evidence_status},
            local_verification_command="dev/verify",
            remote_observations=remotes,
        )
        assert expected in publication["next_action"]


def test_publish_local_readiness_does_not_project_a_publication_plan(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == "lane/topic"
    assert publication["source_role"] == "work_lane"
    assert not {"proposal_branch", "local_proposal_package"} & publication.keys()
    context = publication_domain.observe_publication(
        repo, apply=False, authorized=False, expect_head=None, target_refs=()
    )
    observed = publication_domain.publication_readiness_result(
        context, apply=False, authorized=False, expect_head=None, probe_remote=False
    )
    assert observed.model_dump(mode="json")["data"] == payload["data"]
    assert observed.state == payload["state"]
