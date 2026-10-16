"""Historical accepted bases authorize no new source without current release evidence."""

from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

import ethos.adapters.mutation.accepted.release as release_owner
import ethos.adapters.repo.git_effect_attestation as effect_attestation
import ethos.adapters.repo.git_effects as git_effects
import ethos.adapters.repo.release as release_source
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from tests.support.governed_repository import git
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import maintenance_release_fixture
from tests.unit.cli.land.publication.support import publication_peers
from tests.unit.cli.land.test_release import native_failed_result
from tests.unit.cli.land.test_release import release_cli


@pytest.mark.parametrize("release_mirror", ["independent", "accepted_ff"])
def test_public_maintenance_release_preserves_shared_trains(
    tmp_path: Path, release_mirror: str
) -> None:
    """A new proved maintenance contribution releases only its immutable signed tag."""
    repo, main, base, head = maintenance_release_fixture(tmp_path, release_mirror=release_mirror)
    with patch.object(
        release_source,
        "commit_policy_for_revision",
        wraps=release_source.commit_policy_for_revision,
    ) as policy:
        for count in (1, 2):
            source = release_source.accepted_release_source(repo, head, base=base)
            assert source["head"] == head
            assert source["base"] == base
            assert policy.call_count == count
            assert policy.call_args.args == (repo, git(repo, "rev-parse", "dev"))
    branches = git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads")
    previous = git(main, "rev-parse", "HEAD")
    result = release_cli(
        repo, head, previous, "--release-base", base, "--apply", "--authorize", tag="v1.2.4"
    )
    assert result["verdict"] == "pass", result
    tag = git(repo, "rev-parse", "refs/tags/v1.2.4")
    assert git(repo, "cat-file", "-t", tag) == "tag"
    assert git(repo, "verify-tag", "refs/tags/v1.2.4") == ""
    assert git(repo, "rev-parse", "refs/tags/v1.2.4^{}") == head
    assert git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads") == branches
    repeated = release_cli(
        repo, head, previous, "--release-base", base, "--apply", "--authorize", tag="v1.2.4"
    )
    assert repeated["verdict"] == "pass", repeated
    assert git(repo, "rev-parse", "refs/tags/v1.2.4") == tag
    peers = publication_peers(
        repo, tmp_path, "refs/heads/main", "refs/heads/dev", "refs/heads/candidate/dev"
    )
    before = {name: git(peer, "for-each-ref", "refs/heads") for name, peer in peers.items()}
    preview = branch_publication(repo, head, target_ref="refs/tags/v1.2.4")
    assert preview["verdict"] == "pass", preview
    published = apply_receipt(repo, preview["data"]["request_receipt"], head)
    assert published["verdict"] == "pass", published
    for name, peer in peers.items():
        assert git(peer, "rev-parse", "refs/tags/v1.2.4") == tag
        assert git(peer, "rev-parse", "refs/tags/v1.2.4^{}") == head
        assert git(peer, "for-each-ref", "refs/heads") == before[name]
    assert git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads") == branches


@pytest.mark.parametrize("missing", ["proof", "lease", "renewed"])
def test_maintenance_requires_current_proof_and_live_holder(tmp_path, missing):
    """Historical acceptance cannot substitute for new-source proof or live coordination."""
    repo, main, base, head = maintenance_release_fixture(tmp_path)
    if missing == "proof":
        selected, records = read_attestation_set(repo)
        git(repo, "update-ref", "-d", ATTESTATION_SET_REF, selected)
        record_attestations(
            repo,
            tuple(
                record
                for record in records
                if not (
                    record.predicate == "proof:execution" and record.subject == f"git:commit:{head}"
                )
            ),
        )
    else:
        branch = git(repo, "branch", "--show-current")
        current = leases_by_branch(repo)[branch]
        apply_lease_operation(
            state_database(repo),
            request=LeaseOperationRequest(
                operation="renew" if missing == "renewed" else "transfer",
                branch=branch,
                holder_ref=current["holder_ref"],
                generation=current["generation"],
                expires_at=current["expires_at"],
                target_holder_ref="agent:test:case:new-holder",
                apply=True,
            ),
        )
    refs = git(repo, "show-ref")
    result = release_cli(
        repo,
        head,
        git(main, "rev-parse", "HEAD"),
        "--release-base",
        base,
        "--apply",
        "--authorize",
        tag="v1.2.4",
        blocked=True,
    )
    assert result["verdict"] == "block", result
    assert result["required_gaps"] == (
        ["proof_not_proven"]
        if missing == "proof"
        else ["proof_lease_generation_stale"]
        if missing == "renewed"
        else ["lease_actor_mismatch"]
    )
    assert git(repo, "show-ref") == refs


@pytest.mark.parametrize("boundary", ["before-cas", "lost-ack", "attestation"])
def test_maintenance_recovers_only_its_native_tag(tmp_path, monkeypatch, boundary):
    """Interruption retains the one tag request and never mutates shared branch trains."""
    repo, main, base, head = maintenance_release_fixture(tmp_path)
    args = (repo, head, git(main, "rev-parse", "HEAD"), "--release-base", base)
    branches = git(repo, "for-each-ref", "refs/heads")
    if boundary == "attestation":
        owner, name = effect_attestation, "records"
    else:
        owner, name = git_effects, "_run_effect_program"
    native = getattr(owner, name)
    with monkeypatch.context() as patch:
        if boundary == "attestation":
            patch.setattr(owner, name, Mock(side_effect=OSError("lost effect receipt")))
        else:

            def interrupt(*values, **options):
                if boundary == "lost-ack":
                    return native_failed_result(
                        native,
                        values,
                        options,
                        scope=patch,
                        boundary="native-ack",
                        root=tmp_path / "reject-hooks",
                    )
                message = "lost native acknowledgement"
                raise OSError(message)

            patch.setattr(owner, name, interrupt)
        result = release_cli(*args, "--apply", "--authorize", tag="v1.2.4", blocked=True)
    assert result["verdict"] == "unknown", result
    tag_before = git(repo, "for-each-ref", "--format=%(objectname)", "refs/tags/v1.2.4")
    recovered = release_cli(*args, "--apply", "--authorize", tag="v1.2.4")
    assert recovered["verdict"] == "pass", recovered
    tag = git(repo, "rev-parse", "refs/tags/v1.2.4")
    assert not tag_before or tag_before == tag
    assert git(repo, "for-each-ref", "refs/heads") == branches
    assert git(repo, "rev-parse", "refs/tags/v1.2.4^{}") == head


def test_maintenance_rejects_lease_renewal_during_compilation(tmp_path, monkeypatch):
    """A proof for G1 cannot authorize a tag compiled after native renewal to G2."""
    repo, main, base, head = maintenance_release_fixture(tmp_path)
    refs = git(repo, "show-ref")
    native = release_owner.create_signed_tag

    def renew_then_prepare(*values, **options):
        branch = git(repo, "branch", "--show-current")
        current = leases_by_branch(repo)[branch]
        apply_lease_operation(
            state_database(repo),
            request=LeaseOperationRequest(
                operation="renew",
                branch=branch,
                holder_ref=current["holder_ref"],
                generation=current["generation"],
                expires_at=current["expires_at"],
                apply=True,
            ),
        )
        return native(*values, **options)

    monkeypatch.setattr(release_owner, "create_signed_tag", renew_then_prepare)
    result = release_cli(
        repo,
        head,
        git(main, "rev-parse", "HEAD"),
        "--release-base",
        base,
        "--apply",
        "--authorize",
        tag="v1.2.4",
        blocked=True,
    )
    assert result["required_gaps"] == ["proof_lease_generation_stale"], result
    assert git(repo, "show-ref") == refs


def test_maintenance_preview_admits_tag_only_release_without_effects(tmp_path: Path) -> None:
    """A preview validates the maintenance release but leaves the tag-only plan to apply."""
    repo, main, base, head = maintenance_release_fixture(tmp_path, release_mirror="independent")
    refs = git(repo, "for-each-ref", "--format=%(refname) %(objectname)")
    previous = git(main, "rev-parse", "HEAD")
    preview = release_cli(repo, head, previous, "--release-base", base, tag="v1.2.4")
    assert preview["verdict"] == "pass", (preview["required_gaps"], preview.get("data"))
    assert git(repo, "for-each-ref", "--format=%(refname) %(objectname)") == refs
    assert not git(repo, "tag", "--list", "v1.2.4")
