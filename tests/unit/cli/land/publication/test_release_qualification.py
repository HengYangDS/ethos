"""A release tag is judged by the proof its release record bound, never by a later policy."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

import ethos.adapters.mutation.proof_admission as proof_admission
import ethos.adapters.mutation.proof_record as proof_record
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.release import release_provenance
from tests.support.governed_repository import git
from tests.unit.cli.land.publication.support import TAG_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import later_policy
from tests.unit.cli.land.publication.support import pre_push
from tests.unit.cli.land.publication.support import released_while_gitlab_was_away

if TYPE_CHECKING:
    from pathlib import Path


def _bound_proof(repo: Path, tag: str) -> str:
    """Read the proof ID that the tag's own release effect embeds."""
    plan = release_provenance(repo, ref=TAG_REF, oid=tag)
    assert plan is not None
    return str(plan.prior_attestations["proof"]["id"])


def test_a_historical_release_publishes_under_its_recorded_policy(tmp_path: Path) -> None:
    """A later policy neither blocks catch-up nor the receipt for a peer that holds the tag."""
    repo, peers, head, accepted = released_while_gitlab_was_away(tmp_path)
    tag = git(repo, "rev-parse", TAG_REF)
    bound = _bound_proof(repo, tag)
    with patch.object(proof_admission, "resolve_proof_policies", later_policy):
        assert pre_push(repo, tag, "0" * len(head)) == (0, [])
        preview = branch_publication(repo, accepted, "--peer", "gitlab", target_ref=TAG_REF)
        assert preview["verdict"] == "pass", preview
        assert preview["data"]["proof_admission"]["attestation"]["id"] == bound
        applied = apply_receipt(repo, preview["data"]["request_receipt"], accepted)
        assert (applied["verdict"], applied["summary"]["remote_push"]) == ("pass", "applied")
        held = branch_publication(repo, accepted, target_ref=TAG_REF)
        assert held["verdict"] == "pass", held
        receipt = apply_receipt(repo, held["data"]["request_receipt"], accepted)
    assert (receipt["verdict"], receipt["state"]) == ("pass", "published"), receipt
    assert receipt["summary"]["remote_push"] == "already_applied"
    attempts = receipt["data"]["remote_effect"]["attempts"]
    assert {attempt["state"] for attempt in attempts} == {"already_applied"}
    for peer in peers.values():
        assert git(peer, "rev-parse", TAG_REF) == tag
    recorded = next(
        item
        for item in read_attestation_set(repo)[1]
        if item.id == receipt["data"]["remote_effect"]["attestation"]["id"]
    )
    assert recorded.payload.body["plan"]["prior_attestations"]["proof"]["id"] == bound


def test_a_branch_keeps_the_current_policy(tmp_path: Path) -> None:
    """Only a release tag with a release record reads its recorded qualification."""
    repo, peers, _head, accepted = released_while_gitlab_was_away(tmp_path)
    before = git(peers["gitlab"], "rev-parse", "refs/heads/main")
    with patch.object(proof_admission, "resolve_proof_policies", later_policy):
        blocked = branch_publication(
            repo, accepted, "--peer", "gitlab", target_ref="refs/heads/main", blocked=True
        )
    assert "proof_attestation_repository_policy_mismatch" in blocked["required_gaps"], blocked
    assert git(peers["gitlab"], "rev-parse", "refs/heads/main") == before


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("missing", "release_qualification_missing"),
        ("altered", "release_qualification_unverified"),
        ("inconsistent", "proof_attestation_recorded_policy_inconsistent"),
    ],
)
def test_an_unverifiable_qualification_refuses_by_name(tmp_path: Path, case: str, gap: str) -> None:
    """The release record must embed a passing proof that verifies and hashes to its policy."""
    repo, peers, head, accepted = released_while_gitlab_was_away(tmp_path)
    tag = git(repo, "rev-parse", TAG_REF)
    original = proof_admission.recorded_proof

    def embedded(root: Path, proven: str, store: Path, recorded: dict[str, object]) -> object:
        changed = {
            "missing": {"proven_commit": recorded["proven_commit"]},
            "altered": {**recorded, "valid_until": recorded["issued_at"]},
        }[case]
        return original(root, proven, store, changed)

    replacement = (
        patch.object(proof_record, "canonical_json_digest", lambda _value: "f" * 64)
        if case == "inconsistent"
        else patch.object(proof_admission, "recorded_proof", embedded)
    )
    with patch.object(proof_admission, "resolve_proof_policies", later_policy), replacement:
        code, hook_gaps = pre_push(repo, tag, "0" * len(head))
        blocked = branch_publication(
            repo, accepted, "--peer", "gitlab", target_ref=TAG_REF, blocked=True
        )
    assert (code, gap in hook_gaps) == (1, True), hook_gaps
    assert gap in blocked["required_gaps"], blocked
    assert git(peers["gitlab"], "for-each-ref", "--format=%(objectname)", TAG_REF) == ""
