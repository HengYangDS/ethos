"""Publish accepted forward work after exact historical identity replacement."""

import json
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

import ethos.adapters.repo.commit.signature as signature_observation
from ethos.adapters.mutation.lane_retirement.absorbed import retire_absorbed_ref
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import write_publication_topology
from tests.support.governed_repository import write_script_gate_policy
from tests.support.proof import seed_executed_proof
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.signature import repair_fixture_history
from tests.support.signature import signature_repository
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import publication_peers


def test_completed_history_repair_resolves_proposal_objects_without_ref_rewrite(tmp_path: Path):
    """An unchanged proposal ref can still name a verified accepted contribution."""
    repo, old, _candidate = signature_repository(tmp_path, coupled=True)
    git(repo, "branch", "proposal/old-signature", old)
    replacement = repair_fixture_history(
        repo, tmp_path / "original.bundle", corrections={old: {"resign": True}}
    )
    assert git(repo, "rev-parse", "proposal/old-signature") == old
    relation = signature_observation.repaired_object_provenance(repo, old=old, new=replacement)
    assert relation is not None
    assert relation["mapping"][old] == replacement
    assert relation["attestation_id"]

    previous, records = read_attestation_set(repo)
    git(repo, "update-ref", "-d", ATTESTATION_SET_REF, previous)
    changed = record_attestations(
        repo,
        tuple(item for item in records if item.predicate != "effect:commit-signature"),
    )
    try:
        assert (
            signature_observation.repaired_object_provenance(repo, old=old, new=replacement) is None
        )
    finally:
        git(repo, "update-ref", ATTESTATION_SET_REF, previous, changed["root"])

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
    peers = publication_peers(
        repo, tmp_path, "HEAD:refs/heads/dev", f"{old}:{PROPOSAL_REF}"
    ).values()
    preview = branch_publication(repo, accepted, "--retire")
    assert {
        report["contribution"]["state"] for report in preview["data"]["push_admission"].values()
    } == {"repaired"}
    assert apply_receipt(repo, preview["data"]["request_receipt"], accepted)["state"] == "retired"
    assert {
        git(peer, "for-each-ref", "--format=%(objectname)", PROPOSAL_REF) for peer in peers
    } == {""}
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
    assert local["contribution"]["state"] == "repaired"
    assert not git(repo, "branch", "--list", "proposal/old-signature")


def test_publication_consumes_repaired_forward_baseline_at_every_boundary(tmp_path: Path) -> None:
    """Range, protected-ref and peer effects agree without bypassing acceptance."""
    repo, old, candidate = signature_repository(tmp_path, coupled=True)
    replacement = repair_fixture_history(
        repo, tmp_path / "original.bundle", corrections={old: {"resign": True}}
    )
    write_publication_topology(candidate)
    write_script_gate_policy(candidate)
    profile = candidate / ".ethos/profile.toml"
    profile.write_text(profile.read_text().replace('"policy-test"', '"signature-fixture"'))
    git(candidate, "add", "-A")
    git(candidate, "commit", "-S", "-m", "fix: declare independent publication peers")
    head = git(candidate, "rev-parse", "HEAD")
    install_fixture_hook_runtime(repo)
    seed_executed_proof(candidate, head)
    accepted = run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        replacement,
        "--candidate-head",
        head,
        "--json",
        cwd=repo,
    )
    assert accepted["verdict"] == "pass", accepted
    peers = publication_peers(
        repo, tmp_path, f"{old}:refs/heads/dev", f"{old}:refs/heads/main"
    ).values()
    report = run_ethos(
        "hook",
        "pre-push",
        "refs/heads/dev",
        head,
        "--remote-head",
        old,
        "--remote",
        "origin",
        "--json",
        cwd=repo,
    )
    assert report["verdict"] == "pass", report
    assert report["data"]["commit_policy_admission"]["integration_baseline"] == replacement
    _require_independent_admission(repo, candidate, old, head, report["data"])
    preview = run_ethos(
        "publish",
        "--ref",
        "refs/heads/dev",
        "--ref",
        "refs/heads/main",
        "--probe-remote",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )
    assert preview["verdict"] == "pass", preview
    assert {
        (update["expected"], update["desired"])
        for target in preview["data"]["remote_effect"]["targets"]
        for update in target["updates"]
    } == {(old, head)}
    assert all(git(peer, "rev-parse", "dev") == old for peer in peers)
    result = apply_receipt(repo, preview["data"]["request_receipt"], head)
    assert result["state"] == "published", result
    assert {git(peer, "rev-parse", ref) for peer in peers for ref in ("dev", "main")} == {head}


def _require_independent_admission(
    repo: Path, candidate: Path, old: str, head: str, admitted: dict
) -> None:
    """Remove one necessary fact at a time without replacing its observing owner."""
    command = (
        "hook",
        "pre-push",
        "refs/heads/dev",
        head,
        "--remote-head",
        old,
        "--remote",
        "origin",
        "--json",
    )
    selected, records = read_attestation_set(repo)
    cases = (
        (admitted["proof_admission"]["attestation"]["id"], "proof_not_proven"),
        (
            admitted["accepted_closeout_effect"]["attestation_id"],
            "accepted_closeout_effect_not_attested",
        ),
    )
    for identity, gap in cases:
        git(repo, "update-ref", "-d", ATTESTATION_SET_REF, selected)
        subset = record_attestations(repo, tuple(item for item in records if item.id != identity))
        try:
            blocked = run_ethos_blocked(*command, cwd=repo)
            assert gap in blocked["required_gaps"], blocked
            assert blocked["data"]["commit_policy_admission"]["update_kind"] == "repair"
            stream = StringIO()
            with redirect_stderr(stream):
                code = execute_hook(
                    repo,
                    "pre-push",
                    ("origin",),
                    stdin=StringIO(f"refs/heads/dev {head} refs/heads/dev {old}\n"),
                )
            assert code == 1
            assert gap in json.loads(stream.getvalue())["required_gaps"]
        finally:
            git(repo, "update-ref", ATTESTATION_SET_REF, selected, str(subset["root"]))
    git(candidate, "commit", "--allow-empty", "-S", "-m", "fix: later candidate")
    later = git(candidate, "rev-parse", "HEAD")
    try:
        blocked = run_ethos_blocked(*command, cwd=repo)
        assert "accepted_ref_move_not_candidate_head" in blocked["required_gaps"], blocked
    finally:
        git(candidate, "update-ref", "refs/heads/candidate/dev", head, later)
