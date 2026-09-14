"""Exact peer publication effects and transport parity."""

from __future__ import annotations

from pathlib import Path

import pytest

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
    dry_run = run_ethos(
        "publish",
        "--ref",
        "refs/tags/v1.2.3",
        "--probe-remote",
        "--expect-head",
        commit,
        "--json",
        cwd=repo,
    )
    assert dry_run["data"]["remote_effect"]["source"] == {
        "kind": "annotated-tag",
        "object_oid": tag,
        "peeled_commit": commit,
        "tree_oid": tree,
        "signature": {
            "verdict": "pass",
            "principal": "test@example.com",
            "fingerprint": fingerprint,
            "trust_anchor_sha256": anchor_sha256,
            "verifier": "git verify-tag",
            "verifier_version": git(repo, "version"),
        },
    }
    assert {
        report["commit_policy_admission"]["baseline_source"]
        for report in dry_run["data"]["push_admission"].values()
    } == {"accepted_closeout_effect"}
    receipt = dry_run["data"]["request_receipt"]
    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    trust = anchor.read_text()
    anchor.write_text("")
    blocked = apply_receipt(repo, receipt, commit, blocked=True)
    assert blocked["required_gaps"] == ["publication_source_signature_drift"]
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
    commit_fixture(repo, "declare unfinished review")
    head = git(repo, "rev-parse", "HEAD")
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


def test_publish_branch_dry_run_and_apply_share_one_plan_and_attestation(
    tmp_path: Path,
) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    dry_run = branch_publication(repo, head)
    receipt = dry_run["data"]["request_receipt"]
    assert Path(receipt["path"]).parent == local_state_root(repo) / "requests" / "publication"
    plan = TransitionPlan.model_validate_json(Path(receipt["path"]).read_bytes())
    assert (dry_run["verdict"], plan.verdict, plan.effect["operation"]) == (
        "pass",
        "pass",
        "git.ref.compare-and-swap",
    )
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}

    direct = branch_publication(repo, head, "--apply", "--authorize")
    assert direct["data"]["transition_plan"] == dry_run["data"]["transition_plan"]
    for remote in remotes.values():
        git(remote, "update-ref", "-d", PROPOSAL_REF)

    applied = apply_receipt(repo, receipt, head)
    set_root, selected = read_attestation_set(repo)
    attestation = next(item for item in selected if item.predicate == "publication:remote-effect")
    assert applied["state"] == "published"
    assert applied["data"]["remote_effect"]["attestation"]["set_root"] == set_root
    assert mutable_json(attestation.payload.body["plan"]) == applied["data"]["transition_plan"]
    assert {proposal_ref(remote) for remote in remotes.values()} == {head}


def test_publish_branch_preflights_all_peers_and_retry_converges(tmp_path: Path) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    receipt = branch_publication(repo, head)["data"]["request_receipt"]
    hook = remotes["github"] / "hooks/pre-receive"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    failed = apply_receipt(repo, receipt, head, blocked=True)
    assert failed["data"]["remote_effect"]["partial_effects"]["applied_peers"] == ["gitlab"]
    hook.unlink()
    recovered = apply_receipt(repo, receipt, head)
    assert recovered["data"]["remote_effect"]["attempts"][0]["state"] == "already_applied"
    assert proposal_ref(remotes["github"]) == head


@pytest.mark.parametrize("active_change", [False, True])
def test_publish_applies_each_peers_multi_ref_set_atomically(
    tmp_path: Path, *, active_change: bool
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

    dry_run = run_ethos(
        "publish",
        "--ref",
        "refs/heads/main",
        "--ref",
        "refs/heads/dev",
        "--probe-remote",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )
    receipt = dry_run["data"]["request_receipt"]
    targets = dry_run["data"]["remote_effect"]["targets"]
    reports = dry_run["data"]["push_admission"]
    main_reports = [report for key, report in reports.items() if key.endswith(":refs/heads/main")]
    assert {report["commit_policy_admission"]["baseline_source"] for report in main_reports} == {
        "accepted_closeout_effect"
    }
    assert {report["commit_policy_admission"]["baseline_commit"] for report in main_reports} == {
        old
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
    assert blocked["data"]["remote_effect"]["partial_effects"] == {
        "applied_peers": ["gitlab"],
        "failed_peer": "github",
        "pending_peers": [],
    }
    assert git(remotes["github"], "rev-parse", "refs/heads/dev") == old
    assert git(remotes["github"], "for-each-ref", "--format=%(objectname)", "refs/heads/main") == ""

    hook.unlink()
    recovered = apply_receipt(repo, receipt, head)
    assert recovered["state"] == "published"
    for remote in remotes.values():
        assert git(remote, "rev-parse", "refs/heads/dev") == head
        assert git(remote, "rev-parse", "refs/heads/main") == head
        if active_change:
            assert "- [ ]" in git(remote, "show", f"{head}:openspec/changes/delivery-work/tasks.md")


def test_publish_sha256_ref_creation_uses_native_exact_cas(tmp_path: Path) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path, object_format="sha256")

    dry_run = branch_publication(repo, head)

    effect = dry_run["data"]["remote_effect"]
    assert len(effect["source"]["object_oid"]) == 64
    assert {update["expected"] for target in effect["targets"] for update in target["updates"]} == {
        "0" * 64
    }
    receipt = dry_run["data"]["request_receipt"]

    applied = apply_receipt(repo, receipt, head)

    assert applied["state"] == "published"
    assert {proposal_ref(remote) for remote in remotes.values()} == {head}


def test_publish_branch_supports_one_declared_gitlab_peer(tmp_path: Path) -> None:
    repo, remotes, _head = branch_publication_fixture(tmp_path)
    release = repo / ".ethos/release.toml"
    parts = release.read_text(encoding="utf-8").split("[[publication.peers]]", 2)
    release.write_text(parts[0] + "[[publication.peers]]" + parts[1], encoding="utf-8")
    head = commit_fixture(repo, "declare GitLab-only publication")
    seed_executed_proof(repo, head)
    request = branch_publication(repo, head)["data"]["request_receipt"]
    payload = apply_receipt(repo, request, head)
    assert [target["id"] for target in payload["data"]["remote_effect"]["targets"]] == ["gitlab"]
    assert proposal_ref(remotes["gitlab"]) == head
