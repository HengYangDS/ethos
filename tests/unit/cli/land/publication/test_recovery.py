"""Publication replay, currentness and partial-effect recovery."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.mutation.publication.request as publication_request
import ethos.adapters.openspec.observation as openspec_observation
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
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
from tests.unit.cli.land.publication.support import unavailable_remote


@pytest.mark.parametrize("apply", [False, True])
def test_unavailable_remote_preserves_unknown_without_false_divergence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, apply: bool
) -> None:
    """Preview and replay preserve the unavailable fact, never a fictitious conflict."""
    repo, remotes, head = branch_publication_fixture(
        tmp_path, source_branch="dev" if not apply else "candidate/dev"
    )
    receipt = branch_publication(repo, head)["data"]["request_receipt"] if apply else {}
    monkeypatch.setattr(publication_observation, "observe_remote_ref", unavailable_remote)
    result = (
        apply_receipt(repo, receipt, head, blocked=True)
        if apply
        else branch_publication(repo, head, target_ref="refs/heads/dev")
    )
    assert result["verdict"] == "unknown"
    assert result["summary"]["remote_push"] == "not_performed"
    assert result["missing_facts_or_evidence"] == result["required_gaps"]
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}
    if apply:
        assert result["state"] == "preflight_unknown"
    else:
        assert result["required_gaps"] == [
            f"publication_remote_observation_unavailable:{peer}:{remote}:refs/heads/dev"
            for peer, remote in (("gitlab", "origin"), ("github", "github"))
        ]
        assert result["data"]["push_admission"] == {}
        assert not any("non_fast_forward" in gap for gap in result["required_gaps"])


@pytest.mark.parametrize(
    ("failed_remote", "state", "applied", "pending"),
    [
        ("origin", "outcome_unknown", [], ["gitlab", "github"]),
        ("github", "partial", ["gitlab"], ["github"]),
    ],
)
def test_publish_unknown_observation_preserves_exact_effect_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_remote: str,
    state: str,
    applied: list[str],
    pending: list[str],
) -> None:
    """Unknown evidence cannot erase a prior applied peer or cause its replay."""
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
        if args and args[0] == "ls-remote" and args[1] == failed_remote and origin_push_applied:
            raise subprocess.TimeoutExpired(
                ("git", *args),
                30,
                output="",
                stderr="post-write observation stalled",
            )
        return original(root, *args, check=check, timeout=timeout)

    monkeypatch.setattr(publication_execution.git, "run_network_git", run_network_git)

    result = apply_receipt(repo, receipt, head, blocked=True)

    assert (result["verdict"], result["state"]) == ("unknown", state)
    assert result["summary"]["remote_push"] == state
    assert result["data"]["remote_effect"]["partial_effects"] == {
        "applied_peers": applied,
        "failed_peer": "",
        "pending_peers": pending,
    }
    assert result["data"]["remote_effect"]["attempts"][0]["state"] == "applied"
    assert proposal_ref(remotes["gitlab"]) == head
    assert proposal_ref(remotes["github"]) == ""
    assert "--probe-remote" in result["next_action"]
    _, attestations = read_attestation_set(repo)
    recorded = next(
        item
        for item in attestations
        if item.id == result["data"]["remote_effect"]["attestation"]["id"]
    )
    assert recorded.verdict == "unknown"
    assert recorded.payload.body["state"] == state

    monkeypatch.setattr(publication_execution.git, "run_network_git", original)
    recovered = apply_receipt(repo, receipt, head)
    assert recovered["state"] == "published"
    attempts = recovered["data"]["remote_effect"]["attempts"]
    assert [(item["id"], item["state"]) for item in attempts] == [
        ("gitlab", "already_applied"),
        ("github", "applied"),
    ]
    assert {proposal_ref(remote) for remote in remotes.values()} == {head}


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


@pytest.mark.parametrize("changed", ["proof", "selection"])
def test_release_receipt_requires_original_proof_and_role(tmp_path: Path, changed: str) -> None:
    """Neither proof replacement nor self-consistent relabeling grants release permission."""
    repo, peers, head = branch_publication_fixture(tmp_path, accepted=True)
    for remote in peers.values():
        git(remote, "update-ref", "refs/heads/main", head)
    report = branch_publication(repo, head, target_ref="refs/heads/main")
    receipt = report["data"]["request_receipt"]
    if changed == "proof":
        selected, previous = read_attestation_set(repo)
        git(repo, "update-ref", "-d", "refs/ethos/attestations-set", selected)
        record_attestations(
            repo, tuple(item for item in previous if item.predicate != "proof:execution")
        )
        seed_executed_proof(repo, head)
    else:
        original = TransitionPlan.model_validate(report["data"]["transition_plan"])
        proof = {**mutable_json(original.prior_attestations["proof"]), "selection": "review_object"}
        changed_plan = publication_request.compile_remote_publication_request(
            root=repo, effect=publication_effect_from_plan(original), proof=proof
        )
        receipt = publication_request.persist_remote_publication_request(repo, changed_plan)
    blocked = apply_receipt(repo, receipt, head, blocked=True)
    assert blocked["required_gaps"] == [
        "publication_proof_drift" if changed == "proof" else "publication_proof_selection_mismatch"
    ]
    assert blocked["data"]["remote_effect"]["attempts"] == []
    assert {proposal_ref(remote) for remote in peers.values()} == {""}


@pytest.mark.parametrize("changed_fact", ["trust", "proof", "policy"])
def test_publication_rechecks_authority_between_independent_peer_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_fact: str,
) -> None:
    """A first peer's success cannot authorize another effect after required facts change."""
    repo, remotes, head = branch_publication_fixture(
        tmp_path, proof=changed_fact == "proof", accepted=changed_fact == "proof"
    )
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
