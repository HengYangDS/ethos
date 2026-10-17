"""Every set update that adds members also removes the members whose lifetime ended."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.custody import store_custody
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation

_START = datetime(2026, 10, 1, tzinfo=UTC)


def _expiring_record(digest: str = "", *, hour: int) -> Attestation:
    """A takeover window that has closed, optionally binding one custody digest."""
    return attestation_fixture(
        predicate="lane-resolution:takeover",
        verifier="agent:test:lifetime-update",
        subject=f"git:branch:work/expired-{hour}",
        issued_at=_START + timedelta(hours=hour),
        payload_kind="lane-resolution:takeover",
        payload_body={"authorization": "window"},
        valid_until=_START + timedelta(hours=hour + 1),
        evidence_refs=(f"custody:sha256:{digest}",) if digest else ("evidence:test:window",),
    )


def _open_window(hour: int) -> Attestation:
    return attestation_fixture(
        predicate="lane-resolution:takeover",
        verifier="agent:test:lifetime-update",
        subject=f"git:branch:work/open-{hour}",
        issued_at=_START + timedelta(hours=hour),
        payload_kind="lane-resolution:takeover",
        payload_body={"authorization": "window"},
        valid_until=datetime.now(UTC) + timedelta(days=30),
        evidence_refs=("evidence:test:window",),
    )


def _proof(commit: str) -> Attestation:
    return attestation_fixture(
        predicate="proof:execution",
        verifier="agent:test:lifetime-update",
        subject=f"git:commit:{commit}",
        issued_at=_START,
        payload_kind="proof:execution",
        payload_body={"head": commit},
        evidence_refs=("evidence:test:proof",),
    )


def _custody_path(repo: Path, digest: str) -> Path:
    return Path(git_common_dir(repo)) / "ethos/custody/sha256" / digest


def _members(repo: Path) -> set[str]:
    return {member.id for member in attestation_set.read_attestation_set(repo)[1]}


def test_update_removes_ended_members_and_keeps_live_ones(tmp_path: Path) -> None:
    """A closed window leaves with the next addition; an open window stays."""
    repo = init_git_repo(tmp_path / "repo")
    closed, live = _expiring_record(hour=1), _open_window(1)
    previous = attestation_set.record_attestations(repo, (closed, live))["root"]
    added = occurrence_attestation(6_001)

    result = attestation_set.record_attestations(repo, (added,))

    assert result["removed"] == (closed.id,)
    assert result["previous_root"] == previous
    assert _members(repo) == {live.id, added.id}


def test_an_update_never_removes_the_members_it_records(tmp_path: Path) -> None:
    """A member presented for recording is claimed now, so the same update keeps it."""
    repo = init_git_repo(tmp_path / "repo")
    first, second = _expiring_record(hour=1), _expiring_record(hour=2)
    attestation_set.record_attestations(repo, (first, second))

    result = attestation_set.record_attestations(repo, (first, occurrence_attestation(6_005)))

    assert result["removed"] == (second.id,)
    assert first.id in _members(repo)


def test_repeated_addition_leaves_the_root_unchanged(tmp_path: Path) -> None:
    """Adding nothing new writes nothing, even while ended members remain."""
    repo = init_git_repo(tmp_path / "repo")
    closed = _expiring_record(hour=1)
    root = attestation_set.record_attestations(repo, (closed,))["root"]

    repeated = attestation_set.record_attestations(repo, (closed,))

    assert repeated == {"root": root, "previous_root": root, "added": (), "removed": ()}
    assert attestation_set.read_attestation_set(repo)[0] == root


def test_cas_loser_recomputes_lifetime_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A writer that loses the race re-observes refs, so it removes what a ref move ended."""
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    superseded = _proof(old)
    attestation_set.record_attestations(repo, (superseded,))
    winner, loser = occurrence_attestation(6_002), occurrence_attestation(6_003)
    original = attestation_set.run_git
    raced: list[bool] = []

    def race_first_swap(root: Path, *arguments: str, **options: Any) -> Any:
        if arguments[:1] == ("update-ref",) and not raced:
            raced.append(True)
            assert attestation_set.record_attestations(repo, (winner,))["removed"] == ()
            commit_fixture_file(repo, "next.txt", "next\n", "advance dev")
        return original(root, *arguments, **options)

    monkeypatch.setattr(attestation_set, "run_git", race_first_swap)
    result = attestation_set.record_attestations(repo, (loser,))

    assert raced == [True]
    assert result["removed"] == (superseded.id,)
    assert _members(repo) == {winner.id, loser.id}


def test_unobservable_lifetime_facts_remove_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without lifetime facts an update stays a pure union and reports the gap."""
    repo = init_git_repo(tmp_path / "repo")
    closed = _expiring_record(hour=1)
    attestation_set.record_attestations(repo, (closed,))

    def unobservable(*_arguments: object) -> object:
        message = "git worktree list unavailable"
        raise OSError(message)

    monkeypatch.setattr(attestation_set, "_lifetime_facts", unobservable)
    added = occurrence_attestation(6_006)
    result = attestation_set.record_attestations(repo, (added,))

    assert (result["removed"], result["lifetime_gap"]) == ((), "git worktree list unavailable")
    assert _members(repo) == {closed.id, added.id}


def test_a_lifetime_defect_fails_the_update_instead_of_hiding_as_a_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only unobservable facts degrade to a gap; a parsing defect still fails before any effect."""
    repo = init_git_repo(tmp_path / "repo")
    root = attestation_set.record_attestations(repo, (_expiring_record(hour=1),))["root"]

    def defective(*_arguments: object) -> object:
        message = "not enough values to unpack"
        raise ValueError(message)

    monkeypatch.setattr(attestation_set, "_lifetime_facts", defective)
    with pytest.raises(ValueError, match="not enough values to unpack"):
        attestation_set.record_attestations(repo, (occurrence_attestation(6_011),))

    assert attestation_set.read_attestation_set(repo)[0] == root


def test_ended_member_custody_leaves_with_its_last_binder(tmp_path: Path) -> None:
    """Custody bytes bound only by an ended member are deleted after the update."""
    repo = init_git_repo(tmp_path / "repo")
    digest = store_custody(repo, b"expired authorization evidence")
    expired = _expiring_record(digest, hour=0)
    attestation_set.record_attestations(repo, (expired,))

    result = attestation_set.record_attestations(repo, (occurrence_attestation(6_004),))

    assert result["removed"] == (expired.id,)
    assert not _custody_path(repo, digest).exists()


def test_custody_a_recorded_member_binds_outlives_an_ended_binder(tmp_path: Path) -> None:
    """Bytes the update's own member binds stay, even when an ended member bound them too."""
    repo = init_git_repo(tmp_path / "repo")
    digest = store_custody(repo, b"shared custody evidence")
    expired = _expiring_record(digest, hour=0)
    attestation_set.record_attestations(repo, (expired,))
    successor = attestation_fixture(
        predicate="observation:evidence-custody",
        verifier="agent:test:lifetime-update",
        subject="input:custody:successor",
        issued_at=_START,
        payload_kind="observation:evidence-custody",
        payload_body={"preserved": "shared custody evidence"},
        evidence_refs=(f"custody:sha256:{digest}",),
    )

    result = attestation_set.record_attestations(repo, (successor,))

    assert result["removed"] == (expired.id,)
    assert _custody_path(repo, digest).read_bytes() == b"shared custody evidence"


def test_custody_cleanup_failure_does_not_fail_a_committed_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After the swap, a failed byte deletion is reported, never raised as a failed record."""
    repo = init_git_repo(tmp_path / "repo")
    digest = store_custody(repo, b"expired evidence kept by a failed deletion")
    expired = _expiring_record(digest, hour=0)
    attestation_set.record_attestations(repo, (expired,))

    def failing_release(*_arguments: object) -> tuple[str, ...]:
        message = "custody store unavailable"
        raise OSError(message)

    monkeypatch.setattr(attestation_set, "release_custody", failing_release)
    added = occurrence_attestation(6_007)
    result = attestation_set.record_attestations(repo, (added,))

    assert (result["added"], result["removed"]) == ((added.id,), (expired.id,))
    assert result["custody_gap"] == "custody store unavailable"
    assert _custody_path(repo, digest).exists()


def test_an_existing_member_above_the_bound_records_again_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The size bound applies to members being added, so a replay of a legacy member is a no-op."""
    repo = init_git_repo(tmp_path / "repo")
    legacy = occurrence_attestation(6_008, payload_bytes=4_096)
    root = attestation_set.record_attestations(repo, (legacy,))["root"]
    monkeypatch.setattr(attestation_set, "MEMBER_BYTES_LIMIT", 1_024)

    replay = attestation_set.record_attestations(repo, (legacy,))

    assert (replay["root"], replay["added"]) == (root, ())
    with pytest.raises(ValueError, match=r"^attestation_member_too_large:"):
        attestation_set.record_attestations(
            repo, (occurrence_attestation(6_009, payload_bytes=4_096),)
        )


def test_a_malformed_custody_reference_is_refused_before_any_effect(tmp_path: Path) -> None:
    """A custody binding must name a SHA-256 digest before the member can enter the set."""
    repo = init_git_repo(tmp_path / "repo")
    root = attestation_set.record_attestations(repo, (occurrence_attestation(6_010),))["root"]
    malformed = attestation_fixture(
        predicate="observation:evidence-custody",
        verifier="agent:test:lifetime-update",
        subject="input:custody:malformed",
        issued_at=_START,
        payload_kind="observation:evidence-custody",
        payload_body={"preserved": "malformed"},
        evidence_refs=("custody:sha256:not-a-digest",),
    )

    with pytest.raises(ValueError, match=r"^attestation_custody_reference_invalid:"):
        attestation_set.record_attestations(repo, (malformed,))

    assert attestation_set.read_attestation_set(repo)[0] == root
