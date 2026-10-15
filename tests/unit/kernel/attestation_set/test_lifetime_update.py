"""Every set update that adds members also removes the members whose lifetime ended."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.custody import store_custody
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    import pytest

    from ethos.contracts.semantic import Attestation

_START = datetime(2026, 10, 1, tzinfo=UTC)


def _lane_record(transition: str, branch: str, *, hour: int) -> Attestation:
    return attestation_fixture(
        predicate="effect:git-ref-update",
        verifier="agent:test:lifetime-update",
        subject=f"git-effect:{transition}:{branch}:{hour}",
        issued_at=_START + timedelta(hours=hour),
        payload_kind="effect:git-ref-update",
        payload_body={"plan": {"policy": {"transition": transition, "subject": branch}}},
        evidence_refs=("evidence:test:lifetime-update",),
    )


def _members(repo: Path) -> set[str]:
    return {member.id for member in attestation_set.read_attestation_set(repo)[1]}


def test_update_removes_ended_members_and_keeps_live_ones(tmp_path: Path) -> None:
    """A completed retirement's lane records leave with the next addition; live ones stay."""
    repo = init_git_repo(tmp_path / "repo")
    start = _lane_record("lane.start", "work/retired", hour=1)
    retire = _lane_record("lane.retire", "work/retired", hour=2)
    live = _lane_record("lane.start", "work/live", hour=1)
    attestation_set.record_attestations(repo, (start, retire, live))
    added = occurrence_attestation(6_001)

    result = attestation_set.record_attestations(repo, (added,))

    assert result["removed"] == tuple(sorted((start.id, retire.id)))
    assert _members(repo) == {live.id, added.id}


def test_repeated_addition_leaves_the_root_unchanged(tmp_path: Path) -> None:
    """Adding nothing new writes nothing, even while ended members remain."""
    repo = init_git_repo(tmp_path / "repo")
    start = _lane_record("lane.start", "work/retired", hour=1)
    retire = _lane_record("lane.retire", "work/retired", hour=2)
    root = attestation_set.record_attestations(repo, (start, retire))["root"]

    repeated = attestation_set.record_attestations(repo, (start,))

    assert repeated == {"root": root, "added": (), "removed": ()}
    assert attestation_set.read_attestation_set(repo)[0] == root


def test_cas_loser_recomputes_removal_and_union(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A writer that loses the race keeps the winner's member and still removes ended ones."""
    repo = init_git_repo(tmp_path / "repo")
    start = _lane_record("lane.start", "work/retired", hour=1)
    retire = _lane_record("lane.retire", "work/retired", hour=2)
    attestation_set.record_attestations(repo, (start, retire))
    winner, loser = occurrence_attestation(6_002), occurrence_attestation(6_003)
    original = attestation_set.run_git
    raced: list[bool] = []

    def race_first_swap(root: Path, *arguments: str, **options: Any) -> Any:
        if arguments[:1] == ("update-ref",) and not raced:
            raced.append(True)
            attestation_set.record_attestations(repo, (winner,))
        return original(root, *arguments, **options)

    monkeypatch.setattr(attestation_set, "run_git", race_first_swap)
    result = attestation_set.record_attestations(repo, (loser,))

    assert raced == [True]
    assert result["added"] == (loser.id,)
    assert _members(repo) == {winner.id, loser.id}


def test_ended_member_custody_leaves_with_its_last_binder(tmp_path: Path) -> None:
    """Custody bytes bound only by an ended member are deleted after the update."""
    repo = init_git_repo(tmp_path / "repo")
    digest = store_custody(repo, b"expired authorization evidence")
    expired = attestation_fixture(
        predicate="lane-resolution:takeover",
        verifier="agent:test:lifetime-update",
        subject="git:branch:work/expired",
        issued_at=_START,
        payload_kind="lane-resolution:takeover",
        payload_body={"authorization": "window"},
        valid_until=_START + timedelta(hours=1),
        evidence_refs=(f"custody:sha256:{digest}",),
    )
    attestation_set.record_attestations(repo, (expired,))

    result = attestation_set.record_attestations(repo, (occurrence_attestation(6_004),))

    assert result["removed"] == (expired.id,)
    assert not (Path(git_common_dir(repo)) / "ethos/custody/sha256" / digest).exists()
