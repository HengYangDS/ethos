"""Each Attestation has one lifetime that ends only on positive evidence."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

import pytest

from ethos.adapters.repo.attestation_lifetime import LifetimeFacts
from ethos.adapters.repo.attestation_lifetime import ended
from ethos.adapters.repo.attestation_lifetime import lifetime
from tests.support.semantic import attestation_fixture

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation

_START = datetime(2026, 10, 1, tzinfo=UTC)
_C0, _C1, _C2 = ("0" * 39 + "a", "0" * 39 + "b", "0" * 39 + "c")


def _member(
    predicate: str,
    *,
    hour: int = 1,
    subject: str = "input:lifetime",
    body: dict[str, Any] | None = None,
    valid_until: datetime | None = None,
) -> Attestation:
    return attestation_fixture(
        predicate=predicate,
        verifier="agent:test:lifetime",
        subject=subject,
        issued_at=_START + timedelta(hours=hour),
        payload_kind="effect:test",
        payload_body=body or {"hour": hour},
        valid_until=valid_until,
        evidence_refs=("evidence:test:lifetime",),
    )


def _ref_update(
    transition: object, updates: dict[str, tuple[str, str]], *, hour: int = 1, **policy: str
) -> Attestation:
    effect = {ref: {"expected": old, "desired": new} for ref, (old, new) in updates.items()}
    plan = {"policy": {"transition": transition, **policy}, "effect": {"updates": effect}}
    return _member("effect:git-ref-update", hour=hour, body={"plan": plan})


def _publication(commit: str, peer: str, *, hour: int) -> Attestation:
    update = {"expected": _C0, "desired": commit, "target_ref": "refs/heads/dev"}
    effect = {"targets": [{"id": peer, "updates": [update]}]}
    return _member(
        "publication:remote-effect",
        hour=hour,
        subject=f"git:commit:{commit}",
        body={"plan": {"effect": effect}},
    )


def _facts(
    refs: dict[str, str] | None = None,
    *,
    absent: tuple[str, ...] = (),
    pinned: tuple[str, ...] = (),
) -> LifetimeFacts:
    return LifetimeFacts(
        refs=refs or {"refs/heads/dev": _C2},
        pinned=frozenset(pinned),
        absent_objects=frozenset(absent),
        now=datetime(2026, 10, 16, tzinfo=UTC),
    )


def test_lifetime_classifies_product_members() -> None:
    """Each product member names exactly one lifetime and its holder."""
    takeover = _member("lane-resolution:takeover", valid_until=datetime(2026, 10, 2, tzinfo=UTC))
    cases = (
        (
            _ref_update("lane.start", {"refs/heads/work/a": (_C0, _C1)}, subject="work/a"),
            ("operation", "work/a"),
        ),
        (_ref_update("lane.refresh", {}, execution_branch="work/a"), ("operation", "work/a")),
        (_ref_update("lane.retire", {}, subject="work/a"), ("operation", "work/a")),
        (_ref_update("lane.retire", {}, branch="work/a"), ("operation", "work/a")),
        (_member("proof:execution", subject=f"git:commit:{_C1}"), ("head", _C1)),
        (
            _ref_update("candidate.accept", {"refs/heads/dev": (_C0, _C1)}, accepted_branch="dev"),
            ("head", _C1),
        ),
        (
            _ref_update(
                "candidate.integrate",
                {"refs/heads/candidate/dev": (_C0, _C2)},
                candidate_branch="candidate/dev",
            ),
            ("head", _C2),
        ),
        (_publication(_C1, "github", hour=1), ("head", _C1)),
        (_ref_update("release.promote", {"refs/tags/v1": (_C0, _C1)}), ("lineage", "refs/tags/v1")),
        (
            _member("effect:commit-signature", body={"coordinates": {"old": _C0}}),
            ("lineage", f"repair:{_C0}"),
        ),
        (
            _member("release:accepted-identity", body={"identity": {"wheel_sha256": "f" * 64}}),
            ("lineage", f"runtime:{'f' * 64}"),
        ),
        (_member("effect:starter-formation"), ("lineage", "repository")),
        (takeover, ("window", takeover.id)),
        (
            _member("observation:git-merge-prepared", body={"observation": {"branch": "work/a"}}),
            ("operation", "work/a"),
        ),
    )
    for member, expected in cases:
        assert lifetime(member) == expected, member.predicate


@pytest.mark.parametrize(
    "member",
    [
        _member("quality:observation"),
        _ref_update(5, {"refs/heads/work/a": (_C0, _C1)}),
        _ref_update("maintainer.unknown", {"refs/heads/work/a": (_C0, _C1)}),
        _member("observation:git-merge-prepared", body={"observation": {"branch": 7}}),
        _member("proof:execution", subject="input:not-a-commit"),
    ],
)
def test_unknown_or_malformed_members_are_open_predicate(member: Attestation) -> None:
    """A member that names no product holder is kept until an admitted release."""
    assert lifetime(member) == ("open-predicate", member.id)
    assert ended((member,), _facts()) == frozenset()


def test_lane_records_outlive_their_retirement() -> None:
    """Accepted proofs still resolve archive intent through a retired lane's records."""
    members = (
        _ref_update("lane.start", {}, hour=1, subject="work/a"),
        _ref_update("lane.refresh", {}, hour=2, execution_branch="work/a"),
        _ref_update("openspec.archive", {}, hour=3, execution_branch="work/a"),
        _ref_update("lane.retire", {}, hour=4, subject="work/a"),
    )

    assert ended(members, _facts()) == frozenset()


def test_superseded_heads_end_unless_a_ref_or_latest_publication_selects_them() -> None:
    """Head records end once no governed ref or peer's latest publication selects them."""
    old = (
        _member("proof:execution", subject=f"git:commit:{_C1}"),
        _ref_update("candidate.accept", {"refs/heads/dev": (_C0, _C1)}, accepted_branch="dev"),
        _publication(_C1, "github", hour=1),
    )
    current = (
        _member("proof:execution", subject=f"git:commit:{_C2}"),
        _ref_update(
            "candidate.accept", {"refs/heads/dev": (_C1, _C2)}, hour=2, accepted_branch="dev"
        ),
        _publication(_C2, "gitlab", hour=2),
    )
    caught_up = _publication(_C2, "github", hour=3)

    assert ended((*old, *current), _facts()) == frozenset()
    assert ended((*old, *current, caught_up), _facts()) == {member.id for member in old}
    assert ended((*old, *current, caught_up), _facts(pinned=(_C1,))) == frozenset()


def test_latest_landing_record_stays_while_its_ref_has_not_moved() -> None:
    """A transition recorded before its ref moves ends only once a later one supersedes it."""
    in_flight = _ref_update(
        "candidate.accept", {"refs/heads/dev": (_C2, _C1)}, hour=5, accepted_branch="dev"
    )
    later = _ref_update(
        "candidate.accept", {"refs/heads/dev": (_C1, _C2)}, hour=6, accepted_branch="dev"
    )

    assert ended((in_flight,), _facts()) == frozenset()
    assert ended((in_flight, later), _facts()) == {in_flight.id}


def test_only_repair_lineage_ends_by_observation() -> None:
    """Repair lineage ends once its pre-repair objects are gone; the other lineages never do."""
    release = _ref_update("release.promote", {"refs/tags/v1": (_C0, _C1)})
    repair = _member("effect:commit-signature", body={"coordinates": {"old": _C0}})
    runtime = _member("release:accepted-identity", body={"identity": {"wheel_sha256": "f" * 64}})
    starter = _member("effect:starter-formation")
    members = (release, repair, runtime, starter)
    present = _facts({"refs/heads/dev": _C2, "refs/tags/v1": _C1})

    assert ended(members, present) == frozenset()
    assert ended(members, _facts(absent=(_C0,))) == {repair.id}


def test_release_lineage_outlives_a_deleted_local_tag() -> None:
    """A tag missing locally is ref absence, which a declared peer can still contradict."""
    release = _ref_update("release.promote", {"refs/tags/v1": (_C0, _C1)})

    assert ended((release,), _facts()) == frozenset()


def test_every_accepted_release_identity_outlives_its_package() -> None:
    """Version admission refuses rollback against every accepted identity, kept or not."""
    runtime = _member("release:accepted-identity", body={"identity": {"wheel_sha256": "f" * 64}})

    assert ended((runtime,), _facts()) == frozenset()


def test_window_ends_after_valid_until() -> None:
    """An authorization window ends at the first update after it closes."""
    closed = _member("lane-resolution:takeover", valid_until=datetime(2026, 10, 2, tzinfo=UTC))
    open_window = _member(
        "lane-resolution:takeover", hour=2, valid_until=datetime(2026, 11, 1, tzinfo=UTC)
    )

    assert ended((closed, open_window), _facts()) == {closed.id}


def test_a_window_on_a_predicate_without_a_product_reader_never_ends_by_itself() -> None:
    """Custody evidence that declares valid_until stays until an admitted release removes it."""
    custody = _member("evidence:custody", valid_until=datetime(2026, 10, 2, tzinfo=UTC))

    assert lifetime(custody) == ("open-predicate", custody.id)
    assert ended((custody,), _facts()) == frozenset()


def test_heads_never_end_without_observed_refs() -> None:
    """Without any observed ref there is no evidence that a head was superseded."""
    proof = _member("proof:execution", subject=f"git:commit:{_C1}")
    facts = LifetimeFacts(
        refs={},
        pinned=frozenset(),
        absent_objects=frozenset(),
        now=datetime(2026, 10, 16, tzinfo=UTC),
    )

    assert ended((proof,), facts) == frozenset()
