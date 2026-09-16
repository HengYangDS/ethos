"""Public proposal retirement preserves accepted content and exact peer state."""

from __future__ import annotations

import json
import subprocess
from contextlib import redirect_stderr
from io import StringIO
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.mutation.publication.retirement as retirement
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import git
from tests.unit.cli.land.publication.support import proposal_ref

if TYPE_CHECKING:
    from pathlib import Path


def retirement_fixture(tmp_path: Path, *, object_format: str = "sha1"):
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
    for remote in ("origin", "github"):
        git(repo, "push", remote, "HEAD:refs/heads/dev", f"{proposal}:{PROPOSAL_REF}")
    return repo, peers, proposal, accepted


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_public_retirement_after_dev_absorption_does_not_wait_for_main(
    tmp_path: Path, object_format: str
) -> None:
    """Reject the old nonzero-only effect model through the real public CLI."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path, object_format=object_format)
    preview = run_ethos(
        "publish",
        "--retire",
        "--ref",
        PROPOSAL_REF,
        "--probe-remote",
        "--expect-head",
        accepted,
        "--json",
        cwd=repo,
    )
    assert preview["state"] == "ready_to_retire"
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}

    applied = apply_receipt(repo, preview["data"]["request_receipt"], accepted)

    assert applied["state"] == "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {""}
    assert git(repo, "rev-parse", "dev") == accepted
    assert git(repo, "rev-parse", "main") == proposal
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
    report = run_ethos_blocked(
        "publish",
        "--retire",
        "--ref",
        target,
        "--probe-remote",
        "--expect-head",
        accepted,
        "--apply",
        "--authorize",
        "--json",
        cwd=repo,
    )
    assert report["verdict"] == "block"
    assert report["state"] != "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {proposal}
    assert {git(peer, "rev-parse", "dev") for peer in peers.values()} == {accepted}


def test_retirement_rechecks_peer_absorption_between_preview_and_effect(tmp_path: Path):
    """A successful preview is not reusable authorization after peer accepted drift."""
    repo, peers, proposal, accepted = retirement_fixture(tmp_path)
    preview = run_ethos(
        "publish",
        "--retire",
        "--ref",
        PROPOSAL_REF,
        "--probe-remote",
        "--expect-head",
        accepted,
        "--json",
        cwd=repo,
    )
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
    preview = run_ethos(
        "publish",
        "--retire",
        "--ref",
        PROPOSAL_REF,
        "--probe-remote",
        "--expect-head",
        accepted,
        "--json",
        cwd=repo,
    )
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
    result = run_ethos(
        "publish",
        "--retire",
        "--ref",
        PROPOSAL_REF,
        "--probe-remote",
        "--expect-head",
        accepted,
        "--json",
        cwd=repo,
    )
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
    preview = run_ethos(
        "publish",
        "--retire",
        "--ref",
        PROPOSAL_REF,
        "--probe-remote",
        "--expect-head",
        accepted,
        "--json",
        cwd=repo,
    )
    assert apply_receipt(repo, preview["data"]["request_receipt"], accepted)["state"] == "retired"
    assert {proposal_ref(peer) for peer in peers.values()} == {""}
