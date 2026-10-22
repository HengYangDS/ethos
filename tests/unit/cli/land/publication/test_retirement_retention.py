"""A closed, unaccepted proposal retires only while an owned retainer keeps its exact tip."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.publication.retirement as retirement
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import git
from tests.unit.cli.land.publication.support import proposal_ref
from tests.unit.cli.land.publication.test_retirement import retirement_fixture

if TYPE_CHECKING:
    from pathlib import Path

_FORGE = "https://github.example/team/repository.git"


def _unaccepted(repo: Path, accepted: str) -> str:
    """Commit one contribution that dev never absorbs, then return dev to its accepted head."""
    (repo / "unaccepted.txt").write_text("not accepted\n")
    git(repo, "add", "unaccepted.txt")
    git(repo, "commit", "-m", "feat: unaccepted proposal")
    tip = git(repo, "rev-parse", "HEAD")
    git(repo, "reset", "--hard", accepted)
    return tip


def test_a_work_lane_that_keeps_the_exact_tip_lets_its_projection_retire(tmp_path, monkeypatch):
    """Deleting the peer projection loses nothing while an owned Work Lane still reaches it."""
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    repo, peers, _proposal, accepted = retirement_fixture(tmp_path)
    tip = _unaccepted(repo, accepted)
    git(repo, "branch", "work/retained", tip)
    for name in peers:
        git(repo, "push", name, f"{tip}:{PROPOSAL_REF}")

    preview = branch_publication(repo, accepted, "--retire")
    assert preview["state"] == "ready_to_retire", preview
    applied = apply_receipt(repo, preview["data"]["request_receipt"], accepted)

    assert applied["state"] == "retired", applied
    assert {proposal_ref(peer) for peer in peers.values()} == {""}
    assert git(repo, "rev-parse", "work/retained") == tip


def test_a_candidate_ref_that_reaches_the_tip_retains_nothing(tmp_path: Path) -> None:
    """Landing resets the candidate ref, so a tip that only it reaches keeps its projection."""
    repo, _peers, _proposal, accepted = retirement_fixture(tmp_path)
    tip = _unaccepted(repo, accepted)
    git(repo, "branch", "candidate/dev", tip)
    git(repo, "push", "github", f"{tip}:{PROPOSAL_REF}")

    report = retirement.proposal_retirement_report(
        repo, target_ref=PROPOSAL_REF, old=tip, remote="github"
    )

    assert report["required_gaps"] == ["proposal_retirement_not_accepted"], report


@pytest.mark.parametrize(
    ("case", "verdict", "gap"),
    [
        ("retained", "pass", None),
        ("names_another_object", "block", "proposal_retirement_not_accepted"),
        ("review_open", "block", "proposal_retirement_review_open"),
        ("provider_denied", "unknown", "proposal_retirement_review_unknown"),
    ],
)
def test_the_closed_review_ref_on_the_same_peer_retains_the_exact_tip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, verdict: str, gap: str | None
) -> None:
    """Only the peer's ref for a closed review of this branch, naming the exact tip, retains it."""
    repo, _peers, _proposal, accepted = retirement_fixture(tmp_path)
    release = repo / ".ethos/release.toml"
    declared = release.read_text().replace(
        'id = "github"\nprovider = "git"\n', 'id = "github"\nprovider = "github"\n', 1
    )
    release.write_text(
        declared.replace(
            'git_remote = "github"\n', f'git_remote = "github"\nforge_repository = "{_FORGE}"\n', 1
        )
    )
    git(repo, "commit", "-am", "chore: declare the GitHub review peer")
    accepted = git(repo, "rev-parse", "HEAD")
    tip = _unaccepted(repo, accepted)
    review_head = accepted if case == "names_another_object" else tip
    git(repo, "push", "github", f"{tip}:{PROPOSAL_REF}", f"{review_head}:refs/pull/7/head")
    branch = PROPOSAL_REF.removeprefix("refs/heads/")
    native = retirement.process.run_command

    def provider_process(root, command, **kwargs):
        if command[0] != "gh":
            return native(root, command, **kwargs)
        assert command[command.index("--repo") + 1] == _FORGE
        open_query = command[command.index("--state") + 1] == "open"
        state = "OPEN" if open_query else "CLOSED"
        rows = [{"number": 7, "state": state, "headRefName": branch, "headRefOid": tip}]
        output = json.dumps([] if open_query and case != "review_open" else rows)
        return subprocess.CompletedProcess(command, int(case == "provider_denied"), output, "")

    monkeypatch.setattr(retirement.process, "run_command", provider_process)
    report = retirement.proposal_retirement_report(
        repo, target_ref=PROPOSAL_REF, old=tip, remote="github"
    )

    assert report["verdict"] == verdict, report
    assert report["required_gaps"] == ([gap] if gap else []), report
    if case == "retained":
        assert report["retention"]["retainers"] == ["refs/pull/7/head"], report
