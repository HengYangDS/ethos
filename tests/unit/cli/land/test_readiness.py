"""Local publication readiness and peer observations never imply a remote effect."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import tomli_w

import ethos.application.publication.inspection as publication_domain
from ethos.application.publication.fallback import fallback_projection
from ethos.application.publication.inspection import publication_readiness
from ethos.contracts.branch.roles import load_branch_role_policy
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_role_policy
from tests.support.proof import seed_executed_proof
from tests.support.runtime_scenarios import install_fixture_hook_runtime


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
    fallback = payload["data"]["local_ci_fallback"]
    assert fallback == payload["data"]["publication"]["fallback_evidence"]
    assert (fallback["evidence_class"], fallback["hosted_ci_status_claimed"]) == (
        "local_fallback",
        False,
    )

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == branch
    assert publication["source_role"] == load_branch_role_policy(Path.cwd()).role_for_branch(branch)
    assert "proposal_branch" not in publication
    assert "local_proposal_package" not in publication
    assert payload["next_action"]


@pytest.mark.parametrize("state", ["admitted", "missing", "unavailable", "not_required", ""])
def test_the_fallback_projects_every_proof_admission_state(state: str) -> None:
    """Each state carries text; an unknown state is unavailable, and no hosted CI is claimed."""
    attestation = {"id": "proof-1"} if state == "admitted" else {}
    action = "ethos prove --full --execute --expect-head abc --json" if state == "missing" else ""
    fallback = fallback_projection(
        {"state": state, "attestation": attestation, "next_action": action}
    )
    assert (fallback["kind"], fallback["evidence_class"]) == ("local_ci_fallback", "local_fallback")
    assert (fallback["state"], fallback["next_action"]) == (state or "unavailable", action)
    assert fallback["attestation_id"] == attestation.get("id", "")
    assert fallback["text"]
    assert fallback["hosted_ci_status_claimed"] is False


def test_publish_falls_back_to_the_proof_of_its_own_head(tmp_path: Path) -> None:
    """The admitted proof Attestation is the fallback; a new head names the full proof."""
    repo, head = _publish_fixture(tmp_path)
    install_fixture_hook_runtime(repo)
    admitted = run_ethos("publish", "--json", cwd=repo)["data"]["local_ci_fallback"]
    assert (admitted["state"], bool(admitted["attestation_id"])) == ("admitted", True)
    (repo / "README.md").write_text("# Changed\n", encoding="utf-8")
    head = commit_fixture(repo, "docs: change the readme")
    blocked = run_ethos("publish", "--json", cwd=repo)
    missing = blocked["data"]["local_ci_fallback"]
    assert (blocked["verdict"], missing["state"]) == ("block", "missing")
    continuation = f"prove --root {repo.resolve().as_posix()} --full --execute --expect-head {head}"
    assert continuation in missing["next_action"]
    assert blocked["next_action"] == missing["next_action"]


def test_a_refused_publish_names_the_declaration_repair(tmp_path: Path) -> None:
    """A retired field blocks readiness and an exact ref alike, and both name the repair."""
    repo, head = _publish_fixture(tmp_path)
    release = repo / ".ethos/release.toml"
    release.write_text(
        release.read_text().replace(
            "[[publication.peers]]",
            '[publication]\nlocal_verification_command = "true"\n\n[[publication.peers]]',
            1,
        ),
        encoding="utf-8",
    )
    head = commit_fixture(repo, "chore(release): keep a retired command")
    seed_executed_proof(repo, head)
    readiness = run_ethos("publish", "--json", cwd=repo)
    exact = run_ethos_blocked(
        "publish",
        "--ref",
        "refs/heads/dev",
        "--probe-remote",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )
    retired = "publication_declaration_field_retired:local_verification_command"
    for result in (readiness, exact):
        assert (result["verdict"], retired in result["required_gaps"]) == ("block", True)
        assert "ethos lane repair-paradigm --apply" in result["next_action"]


@pytest.mark.parametrize("probe_remote", [False, True])
@pytest.mark.parametrize("mode", ["dual", "defaults", "local", "gitlab", "github", "tracking"])
def test_publish_peer_topology_matrix(tmp_path: Path, mode: str, *, probe_remote: bool) -> None:
    repo, head = _publish_fixture(tmp_path)
    release = repo / ".ethos/release.toml"
    declaration = tomllib.loads(release.read_text())
    peers = declaration["publication"]["peers"]
    peers = [
        peer for peer in peers if mode in {"dual", "defaults", "tracking"} or peer["id"] == mode
    ]
    declaration["publication"]["peers"] = (
        [
            {key: value for key, value in peer.items() if key not in {"id", "git_remote"}}
            for peer in peers
        ]
        if mode == "defaults"
        else peers
    )
    release.write_text(tomli_w.dumps(declaration), encoding="utf-8")
    head = commit_fixture(repo, f"docs(release): declare {mode} publication")
    seed_executed_proof(repo, head)
    for peer in peers[:1] if mode == "tracking" else peers:
        target = tmp_path / f"{peer['id']}.git"
        git(tmp_path, "init", "--bare", target.as_posix())
        git(repo, "remote", "add", peer["git_remote"], target.as_posix())
        git(repo, "push", "--set-upstream", peer["git_remote"], "dev")
    assert "origin" not in git(repo, "remote").splitlines()
    args = ("--probe-remote",) if probe_remote else ()
    payload = run_ethos("publish", *args, "--json", cwd=repo)
    assert payload["summary"]["remote_push"] == "not_performed"
    assert set(payload["data"]["remote_observations"]) == {peer["id"] for peer in peers}
    if mode == "local":
        assert payload["verdict"] == "pass"
        assert payload["summary"]["remote_publication_state"] == "local_only"
        assert payload["summary"]["remote_mutation_allowed"] is False
        assert payload["data"]["publication_ref_admissions"] == {}
        if probe_remote:
            blocked = run_ethos_blocked(
                "publish",
                "--ref",
                "refs/heads/dev",
                "--probe-remote",
                "--expect-head",
                head,
                "--json",
                cwd=repo,
            )
            assert "publication_peers_missing" in blocked["required_gaps"]
        return
    if not probe_remote:
        expected = f"ethos publish --ref refs/heads/dev --probe-remote --expect-head {head} --json"
        assert payload["next_action"] == expected
    observations = payload["data"]["remote_observations"]
    assert all(
        observations[peer["id"]]["availability"]["remote"] == peer["git_remote"] for peer in peers
    )
    if mode in {"dual", "defaults"}:
        assert observations["github"]["availability"]["remote"] == "github"
        assert not {"remote_availability", "remote_sync"} & set(payload["data"])
    elif mode in {"gitlab", "github"}:
        assert payload["data"]["remote_topology"]["state"] == "ready"
    else:
        assert payload["summary"]["remote_sync_states"] == {
            "gitlab": "synchronized",
            "github": "remote_tracking_missing",
        }
        assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"


def test_publication_readiness_selects_fallback_or_admitted_proposal_observation() -> None:
    policy = load_branch_role_policy(Path.cwd())
    proof = f"ethos prove --full --execute --expect-head {'a' * 40} --json"
    unprobed = {"gitlab": {"availability": {"state": "not_probed"}}}
    for branch, action, remotes, expected in (
        ("dev", proof, {}, proof),
        ("dev", "", {}, "ethos publish --ref refs/heads/dev --probe-remote"),
        (policy.work_branch("topic"), proof, unprobed, "refs/heads/proposal/topic"),
        (policy.candidate_branch, "", unprobed, "select an admitted publication target ref"),
    ):
        publication = publication_readiness(
            branch=branch,
            head="a" * 40,
            local_ok=True,
            policy=policy,
            local_ci_fallback={"next_action": action},
            remote_observations=remotes,
        )
        assert expected in publication["next_action"]


def test_publish_local_readiness_does_not_project_a_publication_plan(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "work/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == "work/topic"
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
