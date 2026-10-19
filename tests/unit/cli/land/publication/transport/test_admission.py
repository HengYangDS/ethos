"""Signed input transport keeps destination policy, exact source and peer custody."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.repository.release.publication as release_publication
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.admission.publication import ref_update_admission_report
from ethos.adapters.repo.git_object import zero_oid
from ethos.normalization.coercion import string_sequence
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(("product_proof", "historical"), [(False, True), (True, False)])
def test_declared_signed_transport_shares_publish_and_native_push_admission(
    tmp_path: Path, *, product_proof: bool, historical: bool
) -> None:
    """Object transport preserves trust and CAS without requiring product release proof."""
    repo, peers, prior = branch_publication_fixture(tmp_path, proof=product_proof)
    declaration = repo / ".ethos/release.toml"
    text = declaration.read_text().replace(
        "[publication]\n", '[publication]\ntransport_tags = ["evidence-*"]\n'
    )
    baseline = commit_fixture_file(
        repo, ".ethos/release.toml", text, "test: declare object transport"
    )
    for remote in peers:
        accepted = prior if historical and remote == "gitlab" else baseline
        git(repo, "push", "--no-verify", remote, f"{accepted}:refs/heads/dev")
        git(repo, "push", "--no-verify", remote, f"{prior}:refs/heads/main")
        git(repo, "symbolic-ref", f"refs/remotes/{remote}/HEAD", f"refs/remotes/{remote}/main")
    if historical:
        git(repo, "checkout", "-b", "proposal/historical", prior)
        assert "transport_tags" not in declaration.read_text()
    head = commit_fixture_file(repo, "input.txt", "qualified input\n", "test: qualify input object")
    ref = f"refs/tags/evidence-{head}"
    git(repo, "tag", "-s", "-m", "Exact signed input carrier", ref.removeprefix("refs/tags/"), head)
    tag = git(repo, "rev-parse", ref)
    report = branch_publication(repo, head, "--peer", "github", target_ref=ref)
    assert report["verdict"] == "pass", report
    assert report["data"]["proof_admission"]["selection"] == "review_object"
    native = push_admission_report(
        root=repo, target_ref=ref, pushed_head=tag, remote_head=zero_oid(repo), remote_name="github"
    )
    assert native["verdict"] == "pass", native
    proof = native["proof_admission"]
    destination = native["publication_ref_admission"]
    commits = native["commit_policy_admission"]
    assert isinstance(proof, dict)
    assert isinstance(destination, dict)
    assert isinstance(commits, dict)
    assert proof["selection"] == "review_object"
    assert native["role"] == destination["role"] == "object_transport"
    assert native["policy_ref"] == baseline
    assert commits["revisions"] == [head]
    if historical:
        unselected = push_admission_report(
            root=repo,
            target_ref=ref,
            pushed_head=tag,
            remote_head=zero_oid(repo),
            remote_name="gitlab",
        )
        assert unselected["verdict"] == "block", unselected
    receipt = report["data"]["request_receipt"]
    applied = apply_receipt(repo, receipt, head)
    assert applied["verdict"] == "pass", applied
    assert git(peers["github"], "rev-parse", ref) == tag
    assert git(peers["gitlab"], "for-each-ref", "--format=%(objectname)", ref) == ""
    assert git(repo, "rev-parse", "HEAD") == head
    repeated = apply_receipt(repo, receipt, head)
    assert repeated["verdict"] == "pass", repeated
    assert git(peers["github"], "rev-parse", ref) == tag
    fresh = branch_publication(repo, head, "--peer", "github", target_ref=ref)
    assert fresh["verdict"] == "pass", fresh
    current = fresh["data"]["push_admission"][f"github:{ref}"]
    assert current["role"] == "object_transport"
    assert current["policy_ref"] == baseline
    assert current["commit_policy_admission"]["revisions"] == []


@pytest.mark.parametrize("peer_root", ["native", "missing", "accepted"])
def test_transport_uses_only_the_peer_standard_accepted_authority(
    tmp_path: Path, *, peer_root: str
) -> None:
    """The paradigm fixes role names; only the peer's standard accepted ref supplies policy."""
    repo, peers, prior = branch_publication_fixture(tmp_path, proof=False)
    git(repo, "push", "--no-verify", "github", f"{prior}:refs/heads/main")
    git(repo, "symbolic-ref", "refs/remotes/github/HEAD", "refs/remotes/github/main")
    declaration = repo / ".ethos/release.toml"
    head = commit_fixture_file(
        repo,
        ".ethos/release.toml",
        declaration.read_text().replace(
            "[publication]\n", '[publication]\ntransport_tags = ["evidence-*"]\n'
        ),
        "test: propose object transport scope",
    )
    if peer_root == "missing":
        git(repo, "symbolic-ref", "--delete", "refs/remotes/github/HEAD")
        for branch in ("dev", "main"):
            git(repo, "update-ref", "-d", f"refs/remotes/github/{branch}")
    elif peer_root == "accepted":
        git(repo, "push", "--no-verify", "github", f"{head}:refs/heads/dev")
    ref = f"refs/tags/evidence-{head}"
    git(repo, "tag", "-s", "-m", "Signed policy-bound input", ref.removeprefix("refs/tags/"), head)
    tag = git(repo, "rev-parse", ref)
    native = push_admission_report(
        root=repo, target_ref=ref, pushed_head=tag, remote_head=zero_oid(repo), remote_name="github"
    )
    accepted = peer_root == "accepted"
    expected_verdict = "pass" if accepted else "block"
    assert native["verdict"] == expected_verdict, native
    if accepted:
        assert native["role"] == "object_transport", native
        assert native["policy_ref"] == head, native
    else:
        assert native["policy_ref"] != head, native
    report = branch_publication(
        repo, head, "--peer", "github", target_ref=ref, blocked=not accepted
    )
    assert report["verdict"] == expected_verdict, report
    assert git(peers["github"], "for-each-ref", "--format=%(objectname)", ref) == ""


def test_transport_keeps_native_signature_header_and_immutable_ref_checks(tmp_path: Path) -> None:
    """Review qualification never authorizes an altered tag or an untrusted envelope."""
    repo, _, _ = branch_publication_fixture(tmp_path, proof=False)
    declaration = repo / ".ethos/release.toml"
    text = declaration.read_text().replace(
        "[publication]\n", '[publication]\ntransport_tags = ["evidence-*"]\n'
    )
    head = commit_fixture_file(repo, ".ethos/release.toml", text, "test: declare transport scope")
    git(repo, "push", "--no-verify", "github", f"{head}:refs/heads/dev")
    ref = "refs/tags/evidence-input"
    git(repo, "tag", "-s", "-m", "Signed exact input", "evidence-input", head)
    tag = git(repo, "rev-parse", ref)
    options = {"root": repo, "pushed_head": tag, "remote_name": "github"}
    altered = push_admission_report(
        **options, target_ref="refs/tags/evidence-renamed", remote_head=zero_oid(repo)
    )
    assert "release_tag_name_mismatch" in string_sequence(altered["required_gaps"])
    conflict = push_admission_report(**options, target_ref=ref, remote_head=head)
    assert "release_tag_immutable" in string_sequence(conflict["required_gaps"])
    git(repo, "tag", "-a", "--no-sign", "-m", "Untrusted input", "evidence-unsigned", head)
    unsigned = git(repo, "rev-parse", "refs/tags/evidence-unsigned")
    denied = push_admission_report(
        root=repo,
        pushed_head=unsigned,
        target_ref="refs/tags/evidence-unsigned",
        remote_name="github",
        remote_head=zero_oid(repo),
    )
    assert "release_tag_source_untrusted" in string_sequence(denied["required_gaps"])
    assert git(repo, "rev-parse", ref) == tag


def test_transport_declaration_cannot_downgrade_declared_product_tags(tmp_path: Path) -> None:
    """Product patterns retain release obligations even when transport also matches."""
    repo, _, prior = branch_publication_fixture(tmp_path, proof=False)
    declaration = repo / ".ethos/release.toml"
    text = '[protected_refs]\ntags = ["v*"]\n\n' + declaration.read_text().replace(
        "[publication]\n", '[publication]\ntransport_tags = ["*"]\n'
    )
    head = commit_fixture_file(repo, ".ethos/release.toml", text, "test: preserve release role")
    git(repo, "push", "--no-verify", "github", f"{head}:refs/heads/dev")
    git(repo, "push", "--no-verify", "github", f"{prior}:refs/heads/main")
    git(repo, "symbolic-ref", "refs/remotes/github/HEAD", "refs/remotes/github/main")
    git(repo, "tag", "-s", "-m", "Not a product release", "v9.9.9", head)
    observed = ref_update_admission_report(
        repo,
        target_ref="refs/tags/v9.9.9",
        proposed_head=git(repo, "rev-parse", "v9.9.9"),
        remote_head=zero_oid(repo),
        remote_name="github",
        trusted_baseline=head,
    )
    assert observed["role"] == "release_publication", observed
    report = branch_publication(repo, head, target_ref="refs/tags/v9.9.9", blocked=True)
    assert report["verdict"] == "block"
    assert any("version" in gap or "proof" in gap for gap in report["required_gaps"]), report


@pytest.mark.parametrize("tags", ["evidence-*", [""], ["a", "a"], [1]])
def test_invalid_transport_declaration_is_not_treated_as_absent(
    tmp_path: Path, tags: object
) -> None:
    """Explicit malformed transport ranges are rejected by the sole native owner."""
    topology = release_publication.publication_topology(
        tmp_path,
        {
            "publication": {
                "local_verification_command": "git --version",
                "local_installation_command": "git --version",
                "transport_tags": tags,
                "peers": [],
            }
        },
    )
    assert "publication_transport_tags_invalid" in string_sequence(topology["required_gaps"])


@pytest.mark.parametrize("policy_state", ["withdrawn", "product", "unreadable"])
def test_existing_transport_tag_keeps_current_peer_policy(
    tmp_path: Path, policy_state: str
) -> None:
    """An unchanged tag preserves bytes, not a historical permission to transport them."""
    repo, peers, prior = branch_publication_fixture(tmp_path, proof=False)
    declaration = repo / ".ethos/release.toml"
    source = commit_fixture_file(
        repo,
        ".ethos/release.toml",
        declaration.read_text().replace(
            "[publication]\n", '[publication]\ntransport_tags = ["evidence-*"]\n'
        ),
        "test: accept object transport",
    )
    git(repo, "push", "--no-verify", "github", f"{source}:refs/heads/dev")
    git(repo, "push", "--no-verify", "github", f"{prior}:refs/heads/main")
    git(repo, "symbolic-ref", "refs/remotes/github/HEAD", "refs/remotes/github/main")
    ref = f"refs/tags/evidence-{source}"
    git(repo, "tag", "-s", "-m", "Signed historical input", ref.removeprefix("refs/tags/"), source)
    tag = git(repo, "rev-parse", ref)
    initial = branch_publication(repo, source, "--peer", "github", target_ref=ref)
    applied = apply_receipt(repo, initial["data"]["request_receipt"], source)
    assert applied["verdict"] == "pass", applied
    text = declaration.read_text().replace('transport_tags = ["evidence-*"]\n', "")
    if policy_state == "product":
        text = '[protected_refs]\ntags = ["evidence-*"]\n\n' + text
    policy = commit_fixture_file(repo, ".ethos/release.toml", text, "test: replace peer policy")
    git(repo, "push", "--no-verify", "github", f"{policy}:refs/heads/dev")
    if policy_state == "unreadable":
        git(repo, "symbolic-ref", "--delete", "refs/remotes/github/HEAD")
    git(repo, "checkout", "--detach", source)
    native = push_admission_report(
        root=repo, target_ref=ref, pushed_head=tag, remote_head=tag, remote_name="github"
    )
    assert native["verdict"] == "block", native
    assert native["policy_ref"] != source, native
    if policy_state != "unreadable":
        assert native["policy_ref"] == policy, native
    if policy_state == "product":
        assert native["role"] == "release_publication", native
    preview = branch_publication(repo, source, "--peer", "github", target_ref=ref, blocked=True)
    assert preview["verdict"] == "block", preview
    assert not preview["data"]["request_receipt"], preview
    assert git(peers["github"], "rev-parse", ref) == tag


def test_signed_transport_for_another_head_does_not_persist_a_request(tmp_path: Path) -> None:
    """Source mismatch refuses before durable request creation or any peer effect."""
    repo, peers, prior = branch_publication_fixture(tmp_path, proof=False)
    declaration = repo / ".ethos/release.toml"
    policy = commit_fixture_file(
        repo,
        ".ethos/release.toml",
        declaration.read_text().replace(
            "[publication]\n", '[publication]\ntransport_tags = ["evidence-*"]\n'
        ),
        "test: accept object transport",
    )
    git(repo, "push", "--no-verify", "github", f"{policy}:refs/heads/dev")
    git(repo, "push", "--no-verify", "github", f"{prior}:refs/heads/main")
    git(repo, "symbolic-ref", "refs/remotes/github/HEAD", "refs/remotes/github/main")
    ref = f"refs/tags/evidence-{policy}"
    git(repo, "tag", "-s", "-m", "Earlier signed input", ref.removeprefix("refs/tags/"), policy)
    head = commit_fixture_file(repo, "input.txt", "later source\n", "test: change source after tag")
    report = branch_publication(repo, head, "--peer", "github", target_ref=ref, blocked=True)
    assert "remote_publication_receipt_head_mismatch" in report["required_gaps"], report
    assert not report["data"]["request_receipt"], report
    assert git(peers["github"], "for-each-ref", "--format=%(objectname)", ref) == ""
