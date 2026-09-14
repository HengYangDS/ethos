"""Publication replay, currentness and partial-effect recovery."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.publication.attestation as publication_attestation
import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.mutation.publication.request as publication_request
import ethos.adapters.openspec.observation as openspec_observation
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.value import mutable_json
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.proof import seed_executed_proof
from tests.unit.cli.land.publication.support import PROPOSAL
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import proposal_ref


def test_publish_apply_preflight_unknown_performs_no_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]
    monkeypatch.setattr(
        publication_observation,
        "observe_remote_ref",
        lambda _root, remote, ref: {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "reason": "timeout",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "command": ["git", "ls-remote", remote, ref],
            "cwd": repo.resolve().as_posix(),
            "timeout_seconds": 30,
            "stderr": "transport stalled",
        },
    )

    result = apply_receipt(repo, receipt, head, blocked=True)

    assert (result["verdict"], result["state"]) == ("unknown", "preflight_unknown")
    assert result["summary"]["remote_push"] == "not_performed"
    assert result["missing_facts_or_evidence"] == result["required_gaps"]
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}


def test_publish_post_observation_unknown_reports_the_applied_peer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]
    original = publication_execution.git.run_network_git
    origin_push_applied = False

    def run_network_git(
        root: Path,
        *args: str,
        check: bool = False,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal origin_push_applied
        if args and args[0] == "push":
            completed = original(root, *args, check=check, timeout=timeout)
            if "origin" in args and completed.returncode == 0:
                origin_push_applied = True
            return completed
        if args and args[0] == "ls-remote" and args[1] == "origin" and origin_push_applied:
            raise subprocess.TimeoutExpired(
                ("git", *args),
                30,
                output="",
                stderr="post-write observation stalled",
            )
        return original(root, *args, check=check, timeout=timeout)

    monkeypatch.setattr(publication_execution.git, "run_network_git", run_network_git)

    result = apply_receipt(repo, receipt, head, blocked=True)

    assert (result["verdict"], result["state"]) == ("unknown", "outcome_unknown")
    assert result["summary"]["remote_push"] == "outcome_unknown"
    assert result["data"]["remote_effect"]["partial_effects"] == {
        "applied_peers": [],
        "failed_peer": "",
        "pending_peers": ["gitlab", "github"],
    }
    assert result["data"]["remote_effect"]["attempts"][0]["state"] == "applied"
    assert proposal_ref(remotes["gitlab"]) == head
    assert proposal_ref(remotes["github"]) == ""


def test_publish_branch_retry_records_one_terminal_attestation_after_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retry records the one terminal effect after remote refs already moved."""
    repo, remotes, head = branch_publication_fixture(tmp_path)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]

    with monkeypatch.context() as interrupted:
        interrupted.setattr(
            publication_attestation,
            "record_attestations",
            lambda _root, _attestation: (_ for _ in ()).throw(RuntimeError("interrupted")),
        )
        with pytest.raises(RuntimeError, match="interrupted"):
            apply_receipt(repo, receipt, head)

    assert {proposal_ref(remote) for remote in remotes.values()} == {head}

    recovered = apply_receipt(repo, receipt, head)
    root, attestations = read_attestation_set(repo)
    remote_effects = [
        attestation
        for attestation in attestations
        if attestation.predicate == "publication:remote-effect"
    ]

    assert recovered["state"] == "published"
    assert root == git(repo, "rev-parse", "refs/ethos/attestations-set")
    assert recovered["data"]["remote_effect"]["attempts"] == [
        {
            "id": peer,
            "remote": remote,
            "state": "already_applied",
            "exit_code": 0,
            "stderr": "",
        }
        for peer, remote in (("gitlab", "origin"), ("github", "github"))
    ]
    assert len(remote_effects) == 1
    assert remote_effects[0].payload.body["state"] == "applied"


def test_publish_branch_receipt_rejects_remote_drift_before_any_push(tmp_path: Path) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]
    (repo / "drift.txt").write_text("remote drift\n", encoding="utf-8")
    drift = commit_fixture(repo, "remote drift")
    git(repo, "push", "origin", f"{drift}:{PROPOSAL_REF}")
    git(repo, "reset", "--hard", head)
    blocked = apply_receipt(repo, receipt, head, blocked=True)
    assert blocked["required_gaps"] == [f"publication_target_drift:gitlab:proposal/{PROPOSAL}"]
    assert (proposal_ref(remotes["gitlab"]), proposal_ref(remotes["github"])) == (drift, "")


def test_publish_branch_receipt_rejects_selected_proof_drift_before_any_push(
    tmp_path: Path,
) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    for remote in remotes.values():
        git(remote, "update-ref", "refs/heads/main", head)
    receipt = branch_publication(repo, head, target_ref="refs/heads/main")["data"][
        "request_receipt"
    ]
    selected = git(repo, "rev-parse", "--verify", "refs/ethos/attestations-set")
    git(repo, "update-ref", "-d", "refs/ethos/attestations-set", selected)
    seed_executed_proof(repo, head)

    blocked = apply_receipt(repo, receipt, head, blocked=True)

    assert blocked["required_gaps"] == ["publication_proof_drift"]
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}


def test_replay_cannot_weaken_proof_selection_with_self_consistent_receipt_hash(tmp_path: Path):
    """A caller-controlled review label cannot override a release destination."""
    repo, remotes, head = branch_publication_fixture(tmp_path)
    for remote in remotes.values():
        git(remote, "update-ref", "refs/heads/main", head)
    report = branch_publication(repo, head, target_ref="refs/heads/main")
    original = TransitionPlan.model_validate(report["data"]["transition_plan"])
    proof = mutable_json(original.prior_attestations["proof"])
    assert isinstance(proof, dict)
    proof["selection"] = "review_object"
    changed = publication_request.compile_remote_publication_request(
        root=repo,
        effect=publication_effect_from_plan(original),
        proof=proof,
    )
    receipt = publication_request.persist_remote_publication_request(repo, changed)

    blocked = apply_receipt(repo, receipt, head, blocked=True)

    assert blocked["required_gaps"] == ["publication_proof_selection_mismatch"]
    assert blocked["data"]["remote_effect"]["attempts"] == []


@pytest.mark.parametrize("changed_fact", ["trust", "proof", "policy"])
def test_publication_rechecks_authority_between_independent_peer_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_fact: str,
) -> None:
    """A first peer's success cannot authorize another effect after required facts change."""
    repo, remotes, head = branch_publication_fixture(tmp_path, proof=changed_fact == "proof")
    target = "refs/heads/main" if changed_fact == "proof" else PROPOSAL_REF
    if changed_fact == "proof":
        for remote in remotes.values():
            git(remote, "update-ref", target, git(repo, "rev-parse", f"{head}^"))
    receipt = branch_publication(repo, head, target_ref=target)["data"]["request_receipt"]
    previous = git(remotes["github"], "for-each-ref", "--format=%(objectname)", target)
    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    original = publication_observation.observe_remote_ref
    mutated = False

    def observe(root: Path, remote: str, ref: str):
        nonlocal mutated
        result = original(root, remote, ref)
        if remote == "origin" and result.get("object_oid") == head and not mutated:
            if changed_fact == "trust":
                anchor.write_text("")
            elif changed_fact == "proof":
                git(repo, "update-ref", "-d", "refs/ethos/attestations-set")
            else:
                declaration = repo / ".ethos/release.toml"
                declaration.write_text(
                    declaration.read_text().rsplit("[[publication.peers]]", 1)[0]
                )
            mutated = True
        return result

    monkeypatch.setattr(publication_observation, "observe_remote_ref", observe)

    blocked = apply_receipt(repo, receipt, head, blocked=True)

    assert blocked["state"] == "partial"
    expected = {
        "trust": "publication_source_signature_drift",
        "proof": "proof_not_proven",
        "policy": "publication_remote_target_unknown:github",
    }
    assert expected[changed_fact] in blocked["required_gaps"]
    assert git(remotes["gitlab"], "for-each-ref", "--format=%(objectname)", target) == head
    assert git(remotes["github"], "for-each-ref", "--format=%(objectname)", target) == previous
    assert len(blocked["data"]["remote_effect"]["attempts"]) == 1
    assert blocked["summary"]["remote_push"] == "partial"


@pytest.mark.parametrize("operation", ["pre-push", "dry-run", "apply"])
def test_publication_keeps_unavailable_intent_observation_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """A failed native tree read cannot become a failed policy or an allowed effect."""
    repo, remotes, head = branch_publication_fixture(tmp_path, proof=False)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]
    original = openspec_observation.run_git

    def observe(root: Path, *args: str, check: bool = True):
        if args[0] == "ls-tree" and "openspec/changes" in args:
            return subprocess.CompletedProcess(args, 128, "", "tree unavailable")
        return original(root, *args, check=check)

    monkeypatch.setattr(openspec_observation, "run_git", observe)

    if operation == "apply":
        report = apply_receipt(repo, receipt, head, blocked=True)
        assert report["state"] == "preflight_unknown"
        assert report["data"]["remote_effect"]["attempts"] == []
    elif operation == "dry-run":
        report = branch_publication(repo, head)
    else:
        report = run_ethos_blocked(
            "hook",
            "pre-push",
            PROPOSAL_REF,
            head,
            "--remote-head",
            "0" * 40,
            "--remote",
            "origin",
            "--json",
            cwd=repo,
        )
    assert report["verdict"] == "unknown"
    assert all(
        gap.startswith(f"openspec_ref_tree_unavailable:{head}")
        for gap in report["missing_facts_or_evidence"]
    )
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}


def test_publication_reobserves_an_already_matching_peer_after_another_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A preflight match does not prove a peer still matches after another write."""
    repo, remotes, head = branch_publication_fixture(tmp_path, proof=False)
    baseline = git(repo, "rev-parse", f"{head}^")
    git(remotes["github"], "update-ref", PROPOSAL_REF, head)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]
    original = publication_observation.observe_remote_ref
    changed = False

    def observe(root: Path, remote: str, ref: str):
        nonlocal changed
        result = original(root, remote, ref)
        if remote == "origin" and result.get("object_oid") == head and not changed:
            git(remotes["github"], "update-ref", PROPOSAL_REF, baseline, head)
            changed = True
        return result

    monkeypatch.setattr(publication_observation, "observe_remote_ref", observe)

    report = apply_receipt(repo, receipt, head, blocked=True)

    assert report["state"] == "partial"
    assert report["required_gaps"] == [f"publication_target_drift:github:proposal/{PROPOSAL}"]
    assert (proposal_ref(remotes["gitlab"]), proposal_ref(remotes["github"])) == (head, baseline)
    assert len(report["data"]["remote_effect"]["attempts"]) == 1
