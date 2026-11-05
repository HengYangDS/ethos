"""A release tag is judged by the proof its release record bound, never by a later policy."""

from __future__ import annotations

import json
from contextlib import redirect_stderr
from io import StringIO
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

import ethos.adapters.mutation.proof_admission as proof_admission
import ethos.adapters.mutation.proof_record as proof_record
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.adapters.repo.release import release_provenance
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.proof import seed_executed_proof
from tests.unit.cli.land.publication.support import accepted_release_fixture
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import publication_peers
from tests.unit.cli.land.publication.support import release_cli

if TYPE_CHECKING:
    from pathlib import Path

TAG_REF = "refs/tags/v1.2.3"


def _later_policy(*_args: object, **_kwargs: object) -> tuple[tuple[str, object], ...]:
    """Compile what a later runtime would: a policy no historical proof executed."""
    policy = SimpleNamespace(digest="0" * 64, nodes=(), gaps=())
    return (("full", policy), ("default", policy))


def _pre_push(repo: Path, tag: str, remote_oid: str) -> tuple[int, list[str]]:
    stream = StringIO()
    with redirect_stderr(stream):
        code = execute_hook(
            repo,
            "pre-push",
            ("gitlab",),
            stdin=StringIO(f"{TAG_REF} {tag} {TAG_REF} {remote_oid}\n"),
        )
    output = stream.getvalue()
    return code, json.loads(output)["required_gaps"] if output else []


def _historical_release(tmp_path: Path) -> tuple[Path, dict[str, Path], str, str, str]:
    """Release once to github only, then advance accepted, so the tag is history."""
    repo, _main, old, head = accepted_release_fixture(tmp_path, release_mirror="accepted_ff")
    assert release_cli(repo, head, head, "--apply", "--authorize")["verdict"] == "pass"
    peers = publication_peers(repo, tmp_path, f"{old}:refs/heads/main")
    gitlab = git(repo, "remote", "get-url", "gitlab")
    git(repo, "remote", "set-url", "gitlab", str(tmp_path / "unavailable-gitlab.git"))
    preview = branch_publication(repo, head, "--peer", "github", target_ref=TAG_REF)
    assert apply_receipt(repo, preview["data"]["request_receipt"], head)["state"] == "published"
    git(repo, "remote", "set-url", "gitlab", gitlab)
    candidate = tmp_path / "repo"
    (candidate / "notes").mkdir(exist_ok=True)
    (candidate / "notes/after-release.txt").write_text("accepted later\n", encoding="utf-8")
    accepted = commit_fixture(candidate, "fix: advance accepted after the release")
    seed_executed_proof(candidate, accepted)
    run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--candidate-head",
        accepted,
        "--json",
        cwd=repo,
    )
    return repo, peers, head, accepted, git(repo, "rev-parse", TAG_REF)


def _bound_proof(repo: Path, tag: str) -> str:
    """Read the proof ID that the tag's own release effect embeds."""
    plan = release_provenance(repo, ref=TAG_REF, oid=tag)
    assert plan is not None
    return str(plan.prior_attestations["proof"]["id"])


def test_a_historical_release_publishes_under_its_recorded_policy(tmp_path: Path) -> None:
    """A later policy neither blocks catch-up nor the receipt for a peer that holds the tag."""
    repo, peers, head, accepted, tag = _historical_release(tmp_path)
    bound = _bound_proof(repo, tag)
    with patch.object(proof_admission, "resolve_proof_policies", _later_policy):
        assert _pre_push(repo, tag, "0" * len(head)) == (0, [])
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
    repo, peers, _head, accepted, _tag = _historical_release(tmp_path)
    before = git(peers["gitlab"], "rev-parse", "refs/heads/main")
    with patch.object(proof_admission, "resolve_proof_policies", _later_policy):
        blocked = branch_publication(
            repo, accepted, "--peer", "gitlab", target_ref="refs/heads/main", blocked=True
        )
    assert "proof_attestation_repository_policy_mismatch" in blocked["required_gaps"], blocked
    assert git(peers["gitlab"], "rev-parse", "refs/heads/main") == before


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("missing", "release_qualification_missing"),
        ("altered", "release_qualification_binding_mismatch"),
        ("inconsistent", "proof_attestation_recorded_policy_inconsistent"),
    ],
)
def test_an_unverifiable_qualification_refuses_by_name(tmp_path: Path, case: str, gap: str) -> None:
    """The release-bound proof must exist, equal its embedded copy and hash to its policy."""
    repo, peers, head, accepted, tag = _historical_release(tmp_path)
    bound = _bound_proof(repo, tag)
    original = proof_record.read_attestation_set

    def without_bound(root: Path) -> tuple[object, tuple[object, ...]]:
        selected, members = original(root)
        return selected, tuple(item for item in members if item.id != bound)

    def altered(root: Path) -> tuple[object, tuple[object, ...]]:
        selected, members = original(root)
        return selected, tuple(
            item.model_copy(update={"valid_until": item.issued_at}) if item.id == bound else item
            for item in members
        )

    replacement = {
        "missing": patch.object(proof_record, "read_attestation_set", without_bound),
        "altered": patch.object(proof_record, "read_attestation_set", altered),
        "inconsistent": patch.object(
            proof_record, "canonical_json_digest", lambda _value: "f" * 64
        ),
    }[case]
    with patch.object(proof_admission, "resolve_proof_policies", _later_policy), replacement:
        code, hook_gaps = _pre_push(repo, tag, "0" * len(head))
        blocked = branch_publication(
            repo, accepted, "--peer", "gitlab", target_ref=TAG_REF, blocked=True
        )
    assert (code, gap in hook_gaps) == (1, True), hook_gaps
    assert gap in blocked["required_gaps"], blocked
    assert git(peers["gitlab"], "for-each-ref", "--format=%(objectname)", TAG_REF) == ""
