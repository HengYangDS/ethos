"""The full proof judges the commits that the checkout's next publications will carry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.gates.commit_ranges import commit_ranges_report
from ethos.repository.policy.quality.sources import provider_module_sources
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.registries import repository_registry
from tests.unit.cli.land.publication.support import branch_publication_fixture

if TYPE_CHECKING:
    from pathlib import Path

_PEERS = ("gitlab", "github")


def _fixture(tmp_path: Path, *, main: bool) -> tuple[Path, str]:
    """Return a checkout whose peers' `dev` (and `main`) tips are its head."""
    repo, remotes, head = branch_publication_fixture(tmp_path, source_branch="dev")
    for remote in remotes:
        assert git(repo, "rev-parse", f"refs/remotes/{remote}/dev") == head
        if main:
            git(repo, "push", "-q", remote, f"{head}:refs/heads/main")
    return repo, head


def test_peers_that_share_a_tip_share_one_judged_range(tmp_path: Path) -> None:
    """Two signed commits beyond both peers' dev and main are judged once, for all four holders."""
    repo, _ = _fixture(tmp_path, main=True)
    for name in ("one", "two"):
        head = commit_fixture_file(repo, f"notes/{name}.txt", f"{name}\n", f"docs: add note {name}")
    report = commit_ranges_report(repo, current_head=head)
    assert (report["verdict"], report["required_gaps"]) == ("pass", [])
    [target] = report["targets"]
    assert target["holders"] == [f"{r}/{b}" for r in _PEERS for b in ("dev", "main")]
    assert target["checked_commit_count"] == 2


@pytest.mark.gate("commit-ranges", "conforming")
def test_an_empty_range_passes(tmp_path: Path) -> None:
    """A head that every peer already holds leaves nothing to judge."""
    repo, head = _fixture(tmp_path, main=True)
    report = commit_ranges_report(repo, current_head=head)
    assert report["verdict"] == "pass"
    assert [target["checked_commit_count"] for target in report["targets"]] == [0]


@pytest.mark.gate("commit-ranges", "refusing")
def test_a_commit_the_heads_policy_refuses_blocks(tmp_path: Path) -> None:
    """An unsigned commit in the next range refuses with the head's own commit policy."""
    repo, _ = _fixture(tmp_path, main=True)
    (repo / "notes/three.txt").write_text("three\n", encoding="utf-8")
    git(repo, "add", "--", "notes/three.txt")
    git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "docs: add note three")
    report = commit_ranges_report(repo, current_head=git(repo, "rev-parse", "HEAD"))
    assert report["verdict"] == "block"
    assert any(gap.startswith("commit_signature_missing:") for gap in report["required_gaps"])


@pytest.mark.gate("commit-ranges", "fail_closed")
@pytest.mark.parametrize(
    ("case", "verdict", "gaps", "notes"),
    [
        ("no-peer-remote", "pass", [], ["commit_ranges_no_peer_remote"]),
        ("invalid-declaration", "block", ["publication_topology_declaration_invalid"], []),
        (
            "never-fetched",
            "block",
            ["commit_ranges_unobserved"],
            [f"commit_ranges_peer_unobserved:{r}:{b}" for r in _PEERS for b in ("dev", "main")],
        ),
        (
            "main-unobserved",
            "pass",
            [],
            [f"commit_ranges_peer_unobserved:{r}:main" for r in _PEERS],
        ),
    ],
)
def test_what_the_checkout_cannot_observe(
    tmp_path: Path, case: str, verdict: str, gaps: list[str], notes: list[str]
) -> None:
    """No peer remote applies nothing; a peer never fetched refuses; one missing branch notes."""
    repo, head = _fixture(tmp_path, main=False)
    for remote in _PEERS:
        if case == "no-peer-remote":
            git(repo, "remote", "remove", remote)
        elif case == "never-fetched":
            for branch in ("dev", "main"):
                git(repo, "update-ref", "-d", f"refs/remotes/{remote}/{branch}")
    if case == "invalid-declaration":
        (repo / ".ethos/release.toml").write_text("[publication]\nunknown = 1\n", encoding="utf-8")
    report = commit_ranges_report(repo, current_head=head)
    assert (report["verdict"], report.get("required_gaps", [])) == (verdict, gaps)
    assert [note["code"] for note in report.get("diagnostics", [])] == notes
    assert report["applicable"] is (case != "no-peer-remote")


def test_the_full_proof_runs_the_gate_from_the_candidate_source() -> None:
    """ETHOS's registry plans the gate in the full set, bound to `src/ethos/`, not the wheel."""
    registry = repository_registry()
    assert "commit-ranges" in registry.proof_sets.full
    [(_, source)] = provider_module_sources(registry.registry()["commit-ranges"])
    assert source == "src/ethos/adapters/gates/commit_ranges.py"
