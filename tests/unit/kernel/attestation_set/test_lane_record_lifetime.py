"""A retired lane's records end together once no reader can still select any of its commits."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.repo.attestation_lifetime import LifetimeFacts
from ethos.adapters.repo.attestation_lifetime import ended
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation

_START = datetime(2026, 10, 1, tzinfo=UTC)
_ZERO = "0" * 40
_BASE, _STARTED, _ARCHIVED, _REFRESHED = ("0" * 39 + digit for digit in "1234")


def _record(predicate: str, body: dict[str, Any], *, hour: int) -> Attestation:
    return attestation_fixture(
        predicate=predicate,
        verifier="agent:test:lane-record-lifetime",
        subject="input:lane-record",
        issued_at=_START + timedelta(hours=hour),
        payload_kind=predicate,
        payload_body=body,
        evidence_refs=("evidence:test:lane-record-lifetime",),
    )


def _update(transition: str, lane: str, old: str, new: str, *, hour: int) -> Attestation:
    field = "subject" if transition.startswith("lane.start") or transition == "lane.retire" else ""
    policy = {
        "transition": transition,
        field or "execution_branch": lane,
        "branch": lane,
    }
    effect = {"updates": {f"refs/heads/{lane}": {"expected": old, "desired": new}}}
    body = {"plan": {"policy": policy, "effect": effect}}
    return _record("effect:git-ref-update", body, hour=hour)


def _lane(lane: str, started: str, archived: str, refreshed: str) -> tuple[Attestation, ...]:
    return (
        _update("lane.start", lane, _ZERO, started, hour=1),
        _record("observation:git-merge-prepared", {"observation": {"branch": lane}}, hour=2),
        _update("openspec.archive", lane, started, archived, hour=3),
        _update("lane.refresh", lane, archived, refreshed, hour=4),
        _update("lane.retire", lane, refreshed, _ZERO, hour=5),
    )


def _facts(*reachable: str, refs: dict[str, str] | None = None) -> LifetimeFacts:
    return LifetimeFacts(
        refs=refs or {"refs/heads/dev": _BASE},
        pinned=frozenset(),
        absent_objects=frozenset(),
        now=datetime(2026, 10, 17, tzinfo=UTC),
        reachable=frozenset(reachable),
    )


def test_a_retired_lane_whose_commits_no_reader_reaches_ends_whole() -> None:
    """Archive, refresh, start, merge and retirement records end at the same update."""
    members = _lane("work/a", _STARTED, _ARCHIVED, _REFRESHED)

    assert ended(members, _facts(_BASE)) == frozenset(member.id for member in members)


def test_proof_admission_keeps_a_lane_whose_archive_commit_a_head_reaches() -> None:
    """A selected head that contains the archive commit can still resolve its archived intent."""
    members = _lane("work/a", _STARTED, _ARCHIVED, _REFRESHED)

    assert ended(members, _facts(_BASE, _STARTED, _ARCHIVED)) == frozenset()


def test_proposal_retirement_keeps_a_lane_whose_refreshed_commit_is_accepted() -> None:
    """An accepted refresh replacement still proves a proposal ref's contribution."""
    members = _lane("work/a", _STARTED, _ARCHIVED, _REFRESHED)

    assert ended(members, _facts(_BASE, _REFRESHED)) == frozenset()


def test_a_live_lane_keeps_its_records_even_when_no_commit_is_reached() -> None:
    """Start boundaries, merge recognition and reacquisition read a live lane's records."""
    members = _lane("work/a", _STARTED, _ARCHIVED, _REFRESHED)
    refs = {"refs/heads/dev": _BASE, "refs/heads/work/a": _REFRESHED}

    assert ended(members, _facts(_BASE, refs=refs)) == frozenset()


def test_lane_records_stay_while_reachability_is_unobserved_or_unnamed() -> None:
    """Without observed reachability, or for a lane that names no commit, nothing ends."""
    members = _lane("work/a", _STARTED, _ARCHIVED, _REFRESHED)
    unobserved = LifetimeFacts(
        refs={"refs/heads/dev": _BASE},
        pinned=frozenset(),
        absent_objects=frozenset(),
        now=datetime(2026, 10, 17, tzinfo=UTC),
    )
    merge = {"observation": {"branch": "work/b"}}
    unnamed = (_record("observation:git-merge-prepared", merge, hour=1),)

    assert ended(members, unobserved) == frozenset()
    assert ended(unnamed, _facts(_BASE)) == frozenset()


def _removed_by_next_update(repo: Path, members: tuple[Attestation, ...]) -> dict[str, object]:
    attestation_set.record_attestations(repo, members)
    return attestation_set.record_attestations(repo, (occurrence_attestation(6_301),))


def test_an_update_ends_only_the_lane_no_selected_commit_reaches(
    tmp_path: Path,
) -> None:
    """A worktree HEAD that contains one lane's archive keeps it; a dropped lane ends."""
    repo = init_git_repo(tmp_path / "repo")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "-c", "work/kept")
    kept = commit_fixture_file(repo, "kept.txt", "kept\n", "kept")
    git(repo, "switch", "-q", "--detach", base)
    dropped = commit_fixture_file(repo, "dropped.txt", "dropped\n", "dropped")
    git(repo, "worktree", "add", "--detach", (tmp_path / "head").as_posix(), kept)
    git(repo, "switch", "-q", "dev")
    git(repo, "branch", "-D", "work/kept")
    kept_lane = _lane("work/kept", kept, kept, kept)
    dropped_lane = _lane("work/dropped", dropped, dropped, dropped)

    result = _removed_by_next_update(repo, (*kept_lane, *dropped_lane))

    assert set(result["removed"]) == {member.id for member in dropped_lane}
    assert "lifetime_gap" not in result


def test_a_present_pre_repair_object_keeps_the_lane_it_descends_from(
    tmp_path: Path,
) -> None:
    """A signature repair can still map the lane's commit into selected history."""
    repo = init_git_repo(tmp_path / "repo")
    base = git(repo, "rev-parse", "HEAD")
    lane_commit = commit_fixture_file(repo, "lane.txt", "lane\n", "lane")
    git(repo, "reset", "-q", "--hard", base)
    repair = _record("effect:commit-signature", {"coordinates": {"old": lane_commit}}, hour=6)
    members = (*_lane("work/repaired", lane_commit, lane_commit, lane_commit), repair)

    assert _removed_by_next_update(repo, members)["removed"] == ()


def test_an_unreadable_selected_commit_keeps_lane_records_and_reports_the_gap(
    tmp_path: Path,
) -> None:
    """A selected commit missing locally hides its ancestry, so no lane record ends."""
    repo = init_git_repo(tmp_path / "repo")
    published = "f" * 40
    update = {"expected": _ZERO, "desired": published, "target_ref": "refs/heads/dev"}
    effect = {"targets": [{"id": "github", "updates": [update]}]}
    publication = attestation_fixture(
        predicate="publication:remote-effect",
        verifier="agent:test:lane-record-lifetime",
        subject=f"git:commit:{published}",
        issued_at=_START,
        payload_kind="publication:remote-effect",
        payload_body={"plan": {"effect": effect}},
        evidence_refs=("evidence:test:lane-record-lifetime",),
    )
    lane_commit = commit_fixture_file(repo, "lane.txt", "lane\n", "lane")
    git(repo, "reset", "-q", "--hard", "HEAD~1")
    members = (publication, *_lane("work/gone", lane_commit, lane_commit, lane_commit))

    result = _removed_by_next_update(repo, members)

    assert result["removed"] == ()
    assert result["lifetime_gap"] == "attestation_lifetime_reachability_unavailable"
