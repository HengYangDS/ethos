"""Exact peer publication effects and transport parity."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.proof as proof_owner
import ethos.adapters.mutation.publication.attestation as publication_attestation
import ethos.adapters.mutation.publication.observation as publication_observation
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.value import mutable_json
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import apply_accepted_closeout
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import write_active_commitment
from tests.support.proof import seed_executed_proof
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import proposal_ref
from tests.unit.cli.land.publication.support import signed_publication_fixture


def test_publication_projects_one_trusted_annotated_tag_exactly_to_two_peers(
    tmp_path: Path,
) -> None:
    repo, remotes, commit, tag, tree, fingerprint, anchor_sha256 = signed_publication_fixture(
        tmp_path
    )
    dry_run = branch_publication(repo, commit, target_ref="refs/tags/v1.2.3")
    assert dry_run["data"]["remote_effect"]["source"] == {
        "kind": "annotated-tag",
        "object_oid": tag,
        "peeled_commit": commit,
        "tree_oid": tree,
        "signature": {
            "verdict": "pass",
            "principal": "test@example.invalid",
            "fingerprint": fingerprint,
            "trust_anchor_sha256": anchor_sha256,
            "verifier": "git verify-tag",
            "verifier_version": git(repo, "version"),
        },
    }
    assert {
        report["commit_policy_admission"]["baseline_source"]
        for report in dry_run["data"]["push_admission"].values()
    } == {"accepted_effect"}
    receipt = dry_run["data"]["request_receipt"]
    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    trust = anchor.read_text()
    anchor.write_text("")
    blocked = apply_receipt(repo, receipt, commit, blocked=True)
    assert blocked["required_gaps"] == ["commit_signature_untrusted"]
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}
    anchor.write_text(trust)
    assert apply_receipt(repo, receipt, commit)["state"] == "published"
    for remote in remotes.values():
        assert git(remote, "rev-parse", "refs/tags/v1.2.3") == tag
        assert git(remote, "rev-parse", "refs/tags/v1.2.3^{}") == commit
        assert git(remote, "rev-parse", "refs/tags/v1.2.3^{tree}") == tree


def test_unfinished_review_reaches_native_pre_push_and_receipt_without_product_proof(
    tmp_path: Path,
) -> None:
    """Official unfinished intent can enter review without closing accepted truth."""
    repo, remotes, accepted = branch_publication_fixture(
        tmp_path, source_branch="work/review", proof=False
    )
    write_active_commitment(repo, change_id="review-work")
    head = commit_fixture(repo, "declare unfinished review")
    install_fixture_hook_runtime(repo)

    report = run_ethos(
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
    dry_run = branch_publication(repo, head)
    applied = apply_receipt(repo, dry_run["data"]["request_receipt"], head)

    assert report["verdict"] == "pass"
    assert applied["state"] == "published"
    assert {proposal_ref(remote) for remote in remotes.values()} == {head}
    assert git(repo, "rev-parse", "dev") == accepted
    assert "- [ ]" in (repo / "openspec/changes/review-work/tasks.md").read_text()


@pytest.mark.parametrize(
    ("object_format", "peer_ids", "interrupted"),
    [("sha1", ("gitlab", "github"), False), ("sha256", ("gitlab",), True)],
)
def test_publish_branch_dry_run_and_apply_share_one_plan_and_attestation(
    tmp_path: Path,
    object_format: str,
    peer_ids: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
    *,
    interrupted: bool,
) -> None:
    repo, remotes, head = branch_publication_fixture(
        tmp_path, object_format=object_format, peer_ids=peer_ids
    )
    dry_run = branch_publication(repo, head)
    effect = dry_run["data"]["remote_effect"]
    assert len(effect["source"]["object_oid"]) == (40 if object_format == "sha1" else 64)
    assert {target["id"] for target in effect["targets"]} == set(peer_ids)
    assert {update["expected"] for target in effect["targets"] for update in target["updates"]} == {
        "0" * len(head)
    }
    receipt = dry_run["data"]["request_receipt"]
    assert Path(receipt["path"]).parent == local_state_root(repo) / "requests" / "publication"
    plan = TransitionPlan.model_validate_json(Path(receipt["path"]).read_bytes())
    assert (dry_run["verdict"], plan.verdict, plan.effect["operation"]) == (
        "pass",
        "pass",
        "git.ref.compare-and-swap",
    )
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}

    if interrupted:
        failure = Mock(side_effect=RuntimeError("interrupted"))
        with monkeypatch.context() as patch:
            patch.setattr(publication_attestation, "record_attestations", failure)
            with pytest.raises(RuntimeError, match="interrupted"):
                apply_receipt(repo, receipt, head)
    else:
        direct = branch_publication(repo, head, "--apply", "--authorize")
        assert direct["data"]["transition_plan"] == dry_run["data"]["transition_plan"]
    assert {proposal_ref(remotes[peer]) for peer in peer_ids} == {head}
    applied = apply_receipt(repo, receipt, head)
    set_root, selected = read_attestation_set(repo)
    effects = [item for item in selected if item.predicate == "publication:remote-effect"]
    attestation = effects[0]
    assert applied["state"] == "published"
    assert applied["data"]["remote_effect"]["attestation"]["set_root"] == set_root
    assert mutable_json(attestation.payload.body["plan"]) == applied["data"]["transition_plan"]
    assert len(effects) == (1 if interrupted else 2)
    assert all(item.payload.body["state"] == "applied" for item in effects)
    assert all(
        item["state"] == "already_applied" for item in applied["data"]["remote_effect"]["attempts"]
    )
    assert {proposal_ref(remotes[peer]) for peer in peer_ids} == {head}


@pytest.mark.parametrize("active_change", [False, True])
def test_publish_applies_each_peers_multi_ref_set_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, active_change: bool
) -> None:
    """Incomplete delivery intent does not split source or peer acceptance."""
    repo, remotes, old = branch_publication_fixture(tmp_path)
    (repo / "accepted.txt").write_text("accepted projection\n", encoding="utf-8")
    if active_change:
        write_active_commitment(repo, change_id="delivery-work")
    head = commit_fixture(repo, "prepare accepted projection")
    seed_executed_proof(repo, head)
    apply_accepted_closeout(repo, old, head)
    git(repo, "update-ref", "refs/heads/main", head)
    proof_reads = Mock(wraps=proof_owner.proof_for_repository_transition)
    monkeypatch.setattr(proof_owner, "proof_for_repository_transition", proof_reads)
    network = Mock(wraps=publication_observation.git.run_network_git)
    monkeypatch.setattr(publication_observation.git, "run_network_git", network)
    dry_run = branch_publication(
        repo, head, "--ref", "refs/heads/dev", target_ref="refs/heads/main"
    )
    assert proof_reads.call_count == 1
    assert [call.args[1:] for call in network.call_args_list if call.args[1] == "ls-remote"] == [
        ("ls-remote", remote, "refs/heads/main", "refs/heads/dev")
        for remote in ("origin", "github")
    ]
    receipt = dry_run["data"]["request_receipt"]
    targets = dry_run["data"]["remote_effect"]["targets"]
    reports = dry_run["data"]["push_admission"]
    main_reports = [
        r["commit_policy_admission"] for k, r in reports.items() if k.endswith(":refs/heads/main")
    ]
    assert {(r["baseline_source"], r["baseline_commit"]) for r in main_reports} == {
        ("accepted_effect", head)
    }
    assert {target["id"] for target in targets} == {"gitlab", "github"}
    assert all(
        {update["target_ref"] for update in target["updates"]}
        == {"refs/heads/main", "refs/heads/dev"}
        for target in targets
    )

    hook = remotes["github"] / "hooks/pre-receive"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        '#!/bin/sh\nwhile read old new ref; do [ "$ref" = refs/heads/main ] && exit 1; done\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)

    blocked = apply_receipt(repo, receipt, head, blocked=True)
    assert proof_reads.call_count == 5  # One CLI observation, preflight and two peer boundaries.
    assert blocked["data"]["remote_effect"]["partial_effects"] == {
        "applied_peers": ["gitlab"],
        "failed_peer": "github",
        "pending_peers": [],
    }
    assert git(remotes["github"], "rev-parse", "refs/heads/dev") == old
    assert git(remotes["github"], "for-each-ref", "--format=%(objectname)", "refs/heads/main") == ""

    hook.unlink()
    recovered = apply_receipt(repo, receipt, head)
    assert proof_reads.call_count == 9  # Recovery must freshly observe the same boundaries.
    assert recovered["state"] == "published"
    assert recovered["data"]["remote_effect"]["attempts"][0]["state"] == "already_applied"
    for remote in remotes.values():
        assert git(remote, "rev-parse", "refs/heads/dev", "refs/heads/main").split() == [head, head]
        if active_change:
            assert "- [ ]" in git(remote, "show", f"{head}:openspec/changes/delivery-work/tasks.md")
