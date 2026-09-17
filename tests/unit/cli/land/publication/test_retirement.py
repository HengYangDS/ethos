"""Public proposal retirement preserves accepted content and exact peer state."""

from __future__ import annotations

import json
import subprocess
from contextlib import redirect_stderr
from io import StringIO
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as refresh_effect
import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.mutation.publication.retirement as retirement
import ethos.adapters.repo.commit.rewrite as rewrite
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.contracts.semantic import Attestation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import git
from tests.unit.cli.land.publication.support import proposal_ref

if TYPE_CHECKING:
    from pathlib import Path


def retirement_fixture(tmp_path: Path, *, object_format: str = "sha1", refreshed: bool = False):
    """Give plain Git peers accepted content without a Forge review system."""
    repo, peers, proposal = branch_publication_fixture(
        tmp_path, source_branch="dev", proof=False, object_format=object_format
    )
    git(repo, "branch", "main", proposal)
    policy = repo / ".ethos/release.toml"
    policy.write_text(
        policy.read_text()
        .replace('provider = "gitlab"', 'provider = "git"')
        .replace('provider = "github"', 'provider = "git"')
    )
    git(repo, "add", ".ethos/release.toml")
    git(repo, "commit", "-m", "chore: declare plain Git peers")
    accepted = git(repo, "rev-parse", "HEAD")
    if refreshed:
        candidate, work = tmp_path / "candidate", tmp_path / "work"
        git(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), accepted)
        install_fixture_hook_runtime(repo)
        run_ethos(
            "lane",
            "start",
            "replayed",
            "--path",
            str(work),
            "--holder-ref",
            "agent:test:case:agent-test",
            "--apply",
            "--json",
            cwd=repo,
        )
        git(work, "mv", "proposal.txt", "renamed.txt")
        (work / "contribution.bin").write_bytes(b"\x00preserved contribution\xff")
        git(work, "add", "-A")
        git(work, "commit", "-m", "feat: preserve renamed and binary contribution")
        proposal = git(work, "rev-parse", "HEAD")
        (candidate / "candidate.txt").write_text("independent candidate change\n")
        git(candidate, "add", "-A")
        git(candidate, "commit", "-m", "feat: advance candidate")
        result = run_ethos(
            "lane",
            "refresh-base",
            "--apply",
            "--authorize",
            "--expect-head",
            proposal,
            "--json",
            cwd=work,
        )
        assert result["state"] == "base_refreshed"
        accepted = git(work, "rev-parse", "HEAD")
        git(repo, "reset", "--hard", accepted)
        git(repo, "commit", "--allow-empty", "-S", "-m", "chore: accept refreshed contribution")
        accepted = git(repo, "rev-parse", "HEAD")
    for remote in ("origin", "github"):
        git(repo, "push", remote, "HEAD:refs/heads/dev", f"{proposal}:{PROPOSAL_REF}")
    return repo, peers, proposal, accepted


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
@pytest.mark.parametrize("refreshed", [False, True])
def test_public_retirement_after_dev_absorption_does_not_wait_for_main(
    tmp_path: Path, monkeypatch, object_format: str, *, refreshed: bool
) -> None:
    """Reject the old nonzero-only effect model through the real public CLI."""
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    repo, peers, proposal, accepted = retirement_fixture(
        tmp_path, object_format=object_format, refreshed=refreshed
    )
    main = git(repo, "rev-parse", "main")
    preview = branch_publication(repo, accepted, "--retire")
    assert preview["state"] == "ready_to_retire"
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}

    applied = apply_receipt(repo, preview["data"]["request_receipt"], accepted)

    assert applied["state"] == "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {""}
    assert git(repo, "rev-parse", "dev") == accepted
    assert git(repo, "rev-parse", "main") == main
    replay = apply_receipt(repo, preview["data"]["request_receipt"], accepted)
    assert replay["state"] == "retired"
    assert {item["state"] for item in replay["data"]["remote_effect"]["attempts"]} == {
        "already_applied"
    }


@pytest.mark.parametrize(
    "target", ["refs/heads/dev", "refs/heads/main", "refs/heads/candidate/dev"]
)
def test_retirement_never_deletes_an_integration_or_release_resource(tmp_path: Path, target: str):
    """Explicit retirement cannot reclassify protected/candidate roles as proposals."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    report = branch_publication(
        repo, accepted, "--retire", "--apply", "--authorize", target_ref=target, blocked=True
    )
    assert report["verdict"] == "block"
    assert report["state"] != "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}
    assert {git(peer, "rev-parse", "dev") for peer in peers.values()} == {accepted}


def test_retirement_rechecks_peer_absorption_between_preview_and_effect(tmp_path: Path):
    """A successful preview is not reusable authorization after peer accepted drift."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    preview = branch_publication(repo, accepted, "--retire")
    parent = git(repo, "rev-parse", f"{proposal}^")
    git(peers["github"], "update-ref", "refs/heads/dev", parent, accepted)
    blocked = apply_receipt(repo, preview["data"]["request_receipt"], accepted, blocked=True)
    assert "proposal_retirement_peer_not_accepted" in blocked["required_gaps"]
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}


def test_retirement_rejects_local_unaccepted_and_raw_hook_deletion(tmp_path: Path):
    """The public command and hook share the same accepted-content obligation."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    (repo / "unaccepted.txt").write_text("not accepted\n")
    git(repo, "add", "unaccepted.txt")
    git(repo, "commit", "-m", "feat: unaccepted proposal")
    future = git(repo, "rev-parse", "HEAD")
    git(repo, "reset", "--hard", accepted)
    for name in ("origin", "github"):
        git(repo, "push", name, f"{future}:{PROPOSAL_REF}")
    report = run_ethos_blocked(
        "hook",
        "pre-push",
        PROPOSAL_REF,
        "0" * 40,
        "--remote-head",
        future,
        "--remote",
        "origin",
        "--json",
        cwd=repo,
    )
    assert "proposal_retirement_not_accepted" in report["required_gaps"]
    assert {proposal_ref(peer) for peer in peers.values()} == {future}
    assert proposal != future


@pytest.mark.parametrize("failure", ["rejected", "timeout", "lost_ack"])
def test_retirement_recovers_partial_effects_without_redeleting_completed_peers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
):
    """Actual bare-ref results, not transport exit alone, govern interrupted deletion."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    preview = branch_publication(repo, accepted, "--retire")
    receipt = preview["data"]["request_receipt"]
    native = publication_execution.git.run_network_git
    unavailable = False

    def network(root, *args, **kwargs):
        nonlocal unavailable
        if args[0] == "push" and "github" in args:
            if failure == "rejected":
                return subprocess.CompletedProcess(args, 1, "", "rejected")
            if failure == "lost_ack":
                native(root, *args, **kwargs)
            unavailable = True
            raise subprocess.TimeoutExpired(args, 30)
        if args[0] == "ls-remote" and args[1] == "github" and unavailable:
            raise subprocess.TimeoutExpired(args, 30)
        return native(root, *args, **kwargs)

    monkeypatch.setattr(publication_execution.git, "run_network_git", network)
    result = apply_receipt(repo, receipt, accepted, blocked=True)
    assert result["state"] == ("partial" if failure == "rejected" else "outcome_unknown")
    assert proposal_ref(peers["gitlab"]) == ""
    assert proposal_ref(peers["github"]) == ("" if failure == "lost_ack" else proposal)
    monkeypatch.setattr(publication_execution.git, "run_network_git", native)
    recovered = apply_receipt(repo, receipt, accepted)
    assert recovered["state"] == "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {""}
    assert recovered["data"]["remote_effect"]["attempts"][0]["state"] == "already_applied"


def test_retirement_preserves_unknown_review_in_public_preview(tmp_path: Path, monkeypatch):
    """An unavailable peer fact remains UNKNOWN all the way through the public result."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    native = publication_observation.observe_remote_ref

    def observe(root, remote, ref):
        if ref == "refs/heads/dev":
            return {"state": "unavailable", "object_oid": "", "reason": "timeout"}
        return native(root, remote, ref)

    monkeypatch.setattr(retirement, "observe_remote_ref", observe)
    result = branch_publication(repo, accepted, "--retire")
    assert result["verdict"] == "unknown"
    assert result["state"] == "observation_unknown"
    assert "--retire" in result["next_action"]
    assert f"--expect-head {accepted}" in result["next_action"]
    assert result["data"]["request_receipt"] == {}
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}


def test_native_pre_push_consumes_deletions_instead_of_skipping_them(tmp_path: Path):
    """Git's deletion tuple must reach the same retirement admission as public CLI."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    install_fixture_hook_runtime(repo)
    output = StringIO()
    with redirect_stderr(output):
        code = execute_hook(
            repo,
            "pre-push",
            ("origin",),
            stdin=StringIO(f"(delete) {'0' * 40} refs/heads/dev {accepted}\n"),
        )
    assert code == 1
    assert (
        "proposal_retirement_target_not_proposal" in json.loads(output.getvalue())["required_gaps"]
    )
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}
    preview = branch_publication(repo, accepted, "--retire")
    assert apply_receipt(repo, preview["data"]["request_receipt"], accepted)["state"] == "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {""}


@pytest.mark.parametrize(
    "fault", ["missing", "invalid", "native_timeout", "nonconserving", "ambiguous"]
)
def test_refreshed_retirement_requires_current_complete_evidence(tmp_path, monkeypatch, fault):
    """Exact bytes without valid provenance, or unavailable computation, grant no deletion."""
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    replay = refresh_effect.run_git

    def rebase(root, *args, **kwargs):
        completed = replay(root, *args, **kwargs)
        if fault == "nonconserving" and args[:2] == ("-c", "rebase.updateRefs=false"):
            git(root, "reset", "--hard", "candidate/dev")
        return completed

    monkeypatch.setattr(refresh_effect, "run_git", rebase)
    repo, peers, proposal, accepted = retirement_fixture(tmp_path, refreshed=True)
    selected, records = read_attestation_set(repo)
    refresh = next(r for r in records if rewrite.declares_transition(r, "lane.refresh"))
    if fault == "ambiguous":
        monkeypatch.setattr(
            rewrite, "read_attestation_set", lambda _root: (selected, (*records, refresh))
        )
    native = rewrite.run_command
    temporary = set()

    def run(root, command, **kwargs):
        temporary.add(root)
        if fault == "native_timeout" and command[1] == "merge-tree":
            raise subprocess.TimeoutExpired(command, 30)
        return native(root, command, **kwargs)

    monkeypatch.setattr(rewrite, "run_command", run)
    if fault in {"missing", "invalid"}:
        retained = tuple(r for r in records if r is not refresh)
        if fault == "invalid":
            data = refresh.model_dump(mode="json", exclude={"id"})
            data["payload"]["body"]["plan"]["policy"]["execution_branch"] = "work/unrelated"
            retained += (Attestation.issue(data),)
        git(repo, "update-ref", "-d", ATTESTATION_SET_REF, selected)
        record_attestations(repo, retained)
    report = branch_publication(repo, accepted, "--retire", blocked=fault != "native_timeout")
    assert report["verdict"] == ("unknown" if fault == "native_timeout" else "block")
    if fault == "nonconserving":
        assert {
            v["contribution"]["conservation"]["reason"]
            for v in report["data"]["push_admission"].values()
        } == {"native_composition_mismatch"}
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}
    assert bool(temporary) == (fault in {"native_timeout", "nonconserving"})
    assert all(not path.exists() for path in temporary)


@pytest.mark.parametrize("observation", ["conflict", "missing", "unrelated"])
def test_native_composition_preserves_unresolved_boundaries(tmp_path, observation):
    """Real native conflicts and unavailable input histories cannot certify conservation."""
    repo = init_git_repo(tmp_path / "native")
    base = git(repo, "rev-parse", "HEAD")
    old = commit_fixture_file(repo, "value.txt", "old\n", "old value")
    git(repo, "checkout", "--detach", base)
    candidate = commit_fixture_file(repo, "value.txt", "candidate\n", "candidate value")
    if observation == "missing":
        candidate = "f" * len(candidate)
    if observation == "unrelated":
        candidate = git(repo, "commit-tree", f"{candidate}^{{tree}}", "-m", "unrelated")
    before = git(repo, "show-ref")
    result = rewrite.observe_refresh_conservation(
        repo, rewrite.RewriteEdge(old, old, "", "refresh", candidate)
    )
    assert result["verdict"] == ("block" if observation == "conflict" else "unknown")
    assert git(repo, "show-ref") == before
