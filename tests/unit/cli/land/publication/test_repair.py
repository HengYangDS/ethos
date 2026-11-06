"""Publish accepted forward work after exact historical identity replacement."""

import json
from collections.abc import Iterable
from collections.abc import Iterator
from contextlib import contextmanager
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

import pytest

import ethos.adapters.repo.commit.signature as signature_observation
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.admission.publication import ref_update_admission_report
from ethos.adapters.mutation.lane_retirement.absorbed import retire_absorbed_ref
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import write_publication_topology
from tests.support.proof import seed_executed_proof
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.signature import repair_fixture_history
from tests.support.signature import signature_repository
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import configure_signature_publication
from tests.unit.cli.land.publication.support import proposal_ref
from tests.unit.cli.land.publication.support import publication_peers

SIGNATURE_PREDICATE = "effect:commit-signature"


@contextmanager
def _attestations_without(repo: Path, field: str, value: str) -> Iterator[None]:
    """Select the set without matching attestations for one observation, then restore it."""
    selected, records = read_attestation_set(repo)
    git(repo, "update-ref", "-d", ATTESTATION_SET_REF, selected)
    kept = tuple(item for item in records if getattr(item, field) != value)
    subset = record_attestations(repo, kept)
    root = subset["root"]
    assert isinstance(root, str)
    try:
        yield
    finally:
        git(repo, "update-ref", ATTESTATION_SET_REF, selected, root)


def _pre_push(repo: Path, head: str, remote_head: str, *, blocked: bool = False) -> dict:
    """Admit one dev update as the native pre-push hook does, against an exact peer head."""
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/dev",
        pushed_head=head,
        remote_head=remote_head,
        remote_name="gitlab",
    )
    assert (report["verdict"] != "pass") is blocked, report
    return report


def _land_forward(repo: Path, candidate: Path, baseline: str) -> str:
    """Accept a signed candidate that declares independent publication peers."""
    configure_signature_publication(candidate)
    git(candidate, "add", "-A")
    git(candidate, "commit", "-S", "-m", "fix: declare independent publication peers")
    head = git(candidate, "rev-parse", "HEAD")
    install_fixture_hook_runtime(repo)
    seed_executed_proof(candidate, head)
    closeout = ("--closeout", "--apply", "--authorize", "--expect-head", baseline)
    accepted = run_ethos("land", *closeout, "--candidate-head", head, "--json", cwd=repo)
    assert accepted["verdict"] == "pass", accepted
    return head


def _publish_preview(repo: Path, head: str, old: str, peers: Iterable[Path]) -> dict:
    """Preview both protected branches as exact CAS from the peers' unchanged heads."""
    request = ("--ref", "refs/heads/dev", "--ref", "refs/heads/main", "--probe-remote")
    preview = run_ethos("publish", *request, "--expect-head", head, "--json", cwd=repo)
    assert preview["verdict"] == "pass", preview
    assert {
        (update["expected"], update["desired"])
        for target in preview["data"]["remote_effect"]["targets"]
        for update in target["updates"]
    } == {(old, head)}
    assert all(git(peer, "rev-parse", "dev") == old for peer in peers)
    return preview["data"]["request_receipt"]


def _publish_apply(repo: Path, receipt: dict, head: str, peers: Iterable[Path]) -> None:
    """Apply the previewed receipt and require both protected branches on every peer."""
    result = apply_receipt(repo, receipt, head)
    assert result["state"] == "published", result
    assert {git(peer, "rev-parse", ref) for peer in peers for ref in ("dev", "main")} == {head}


@pytest.mark.parametrize("peer_history", ["original", "repaired"])
def test_completed_history_repair_resolves_proposal_objects_without_ref_rewrite(
    tmp_path: Path, peer_history: str
):
    """An unchanged proposal ref can still name a verified accepted contribution."""
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    git(repo, "branch", "proposal/old-signature", old)
    replacement = repair_fixture_history(
        repo, tmp_path / "original.bundle", corrections={old: {"resign": True}}
    )
    assert git(repo, "rev-parse", "proposal/old-signature") == old
    relation = signature_observation.repaired_object_provenance(repo, old=old, new=replacement)
    assert relation is not None
    mapping = relation["mapping"]
    assert isinstance(mapping, dict)
    assert mapping[old] == replacement
    assert relation["attestation_id"]
    with _attestations_without(repo, "predicate", SIGNATURE_PREDICATE):
        assert (
            signature_observation.repaired_object_provenance(repo, old=old, new=replacement) is None
        )

    write_publication_topology(repo)
    release = repo / ".ethos/release.toml"
    release.write_text(
        release.read_text()
        .replace('provider = "gitlab"', 'provider = "git"')
        .replace('provider = "github"', 'provider = "git"')
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-S", "-m", "fix: declare Git publication")
    accepted = git(repo, "rev-parse", "HEAD")
    peer_accepted = old if peer_history == "original" else accepted
    peers = publication_peers(
        repo, tmp_path, f"{peer_accepted}:refs/heads/dev", f"{old}:{PROPOSAL_REF}"
    ).values()
    preview = branch_publication(repo, accepted, "--retire")
    assert preview["verdict"] == "pass", preview
    assert {
        report["contribution"]["state"] for report in preview["data"]["push_admission"].values()
    } == {"repaired"}
    assert apply_receipt(repo, preview["data"]["request_receipt"], accepted)["state"] == "retired"
    assert {proposal_ref(peer) for peer in peers} == {""}
    local = retire_absorbed_ref(
        root=repo,
        branch="proposal/old-signature",
        expect_head=old,
        accepted_head=accepted,
        apply=True,
        authorize=True,
        confirm_irreversible=True,
    )
    assert local["state"] == "retired_absorbed_ref"
    contribution = local["contribution"]
    assert isinstance(contribution, dict)
    assert contribution["state"] == "repaired"
    assert not git(repo, "branch", "--list", "proposal/old-signature")


def test_publication_consumes_repaired_forward_baseline_at_every_boundary(tmp_path: Path) -> None:
    """Range, protected-ref and peer effects agree without bypassing acceptance."""
    repo, old, candidate = signature_repository(tmp_path, coupled=True)
    replacement = repair_fixture_history(
        repo, tmp_path / "original.bundle", corrections={old: {"resign": True}}
    )
    head = _land_forward(repo, candidate, replacement)
    peers = publication_peers(
        repo, tmp_path, f"{old}:refs/heads/dev", f"{old}:refs/heads/main"
    ).values()
    report = _pre_push(repo, head, old)
    assert report["verdict"] == "pass", report
    assert report["commit_policy_admission"]["integration_baseline"] == replacement
    _require_independent_admission(repo, candidate, old, head, report)
    receipt = _publish_preview(repo, head, old, peers)
    _publish_apply(repo, receipt, head, peers)


def _historical_peer_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, str, str, str]:
    """Accept forward content after repairing a lagging peer's original history."""
    repo, old, candidate = signature_repository(tmp_path, coupled=True)
    (repo / "notes").mkdir(exist_ok=True)
    (repo / "notes/peer-prefix.txt").write_text("peer prefix\n", encoding="utf-8")
    git(repo, "add", "notes/peer-prefix.txt")
    with monkeypatch.context() as scope:
        scope.setenv("GIT_AUTHOR_NAME", "Wrong")
        scope.setenv("GIT_AUTHOR_EMAIL", "wrong@example.invalid")
        git(repo, "commit", "-S", "-m", "legacy peer prefix")
    peer_old = git(repo, "rev-parse", "HEAD")
    (repo / "notes/old-tip.txt").write_text("old tip\n", encoding="utf-8")
    git(repo, "add", "notes/old-tip.txt")
    git(repo, "commit", "-S", "-m", "fix: old tip")
    old_tip = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", old_tip)
    git(repo, "update-ref", "refs/heads/main", old_tip, old)
    wrong = {"name": "Wrong", "email": "wrong@example.invalid"}
    fixed = {"name": "ETHOS Test", "email": "test@example.invalid"}
    corrections = {peer_old: {"author": {"expected": wrong, "replacement": fixed}}}
    replacement = repair_fixture_history(
        repo, tmp_path / "original.bundle", corrections=corrections
    )
    head = _land_forward(repo, candidate, replacement)
    return repo, candidate, peer_old, replacement, head


def test_historical_peer_prefix_uses_verified_replacement_tip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lagging peer is mapped by repair evidence, not rescanned as new work."""
    repo, candidate, peer_old, replacement, head = _historical_peer_fixture(tmp_path, monkeypatch)
    peers = publication_peers(
        repo, tmp_path, f"{peer_old}:refs/heads/dev", f"{peer_old}:refs/heads/main"
    ).values()
    report = _pre_push(repo, head, peer_old)
    assert report["verdict"] == "pass", report
    commits = report["commit_policy_admission"]
    assert commits["integration_baseline"] == replacement
    assert commits["revisions"] == [head]
    _require_independent_admission(repo, candidate, peer_old, head, report)
    bad = git(repo, "commit-tree", "-S", f"{head}^{{tree}}", "-p", head, "-m", "invalid forward")
    bad_range = ref_update_admission_report(
        repo,
        target_ref="refs/heads/dev",
        proposed_head=bad,
        remote_head=peer_old,
        remote_name="gitlab",
    )["commit_policy_admission"]
    assert isinstance(bad_range, dict)
    assert bad_range["integration_baseline"] == replacement
    assert {item["commit"] for item in bad_range["violations"]} == {bad}
    receipt = _publish_preview(repo, head, peer_old, peers)
    with _attestations_without(repo, "predicate", SIGNATURE_PREDICATE):
        blocked = _pre_push(repo, head, peer_old, blocked=True)
        assert blocked["commit_policy_admission"]["update_kind"] == "existing"
        assert any(gap.startswith("commit_subject_invalid:") for gap in blocked["required_gaps"])
    _publish_apply(repo, receipt, head, peers)


def _require_independent_admission(
    repo: Path, candidate: Path, old: str, head: str, admitted: dict
) -> None:
    """Remove one necessary fact at a time without replacing its observing owner."""
    cases = (
        (admitted["proof_admission"]["attestation"]["id"], "proof_not_proven"),
        (
            admitted["accepted_closeout_effect"]["attestation_id"],
            "accepted_closeout_effect_not_attested",
        ),
    )
    update = f"refs/heads/dev {head} refs/heads/dev {old}\n"
    for identity, gap in cases:
        with _attestations_without(repo, "id", identity):
            blocked = _pre_push(repo, head, old, blocked=True)
            assert gap in blocked["required_gaps"], blocked
            assert blocked["commit_policy_admission"]["update_kind"] == "repair"
            stream = StringIO()
            with redirect_stderr(stream):
                code = execute_hook(repo, "pre-push", ("gitlab",), stdin=StringIO(update))
            assert code == 1
            assert gap in json.loads(stream.getvalue())["required_gaps"]
    git(candidate, "commit", "--allow-empty", "-S", "-m", "fix: later candidate")
    later = git(candidate, "rev-parse", "HEAD")
    try:
        blocked = _pre_push(repo, head, old, blocked=True)
        assert "accepted_ref_move_not_candidate_head" in blocked["required_gaps"], blocked
    finally:
        git(candidate, "update-ref", "refs/heads/candidate/dev", head, later)
