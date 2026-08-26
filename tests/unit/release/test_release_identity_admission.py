from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.transition as release_transition
from ethos.contracts.semantic import Attestation
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import release_identity_admission_gaps
from ethos.repository.release.identity import build_identity

if TYPE_CHECKING:
    from pathlib import Path


def _release(
    version: str,
    *,
    commit: str = "a" * 40,
    tree: str = "b" * 40,
    wheel: str = "c" * 64,
):
    return accepted_release_identity(
        build_identity(
            product=version,
            source_commit=commit,
            source_tree=tree,
            channel="accepted",
            acceptance_state="accepted",
        ),
        wheel_sha256=wheel,
    )


def test_local_only_first_release_and_exact_replay_are_admitted() -> None:
    candidate = _release("0.2.0-alpha.1")

    assert release_identity_admission_gaps(candidate, ()) == ()
    assert release_identity_admission_gaps(candidate, (candidate,)) == ()


@pytest.mark.parametrize(
    ("prior", "candidate", "gap"),
    [
        (
            _release("0.2.0-alpha.2"),
            _release("0.2.0-alpha.1", commit="e" * 40, tree="f" * 40),
            "accepted_version_rollback:0.2.0-alpha.1<0.2.0-alpha.2",
        ),
        (
            _release("0.2.0-alpha.1"),
            _release("0.2.0-alpha.1", commit="e" * 40, tree="f" * 40),
            "accepted_version_source_conflict:0.2.0-alpha.1",
        ),
        (
            _release("0.2.0-alpha.1"),
            _release("0.2.0-alpha.1", wheel="e" * 64),
            "accepted_version_artifact_conflict:0.2.0-alpha.1",
        ),
    ],
)
def test_release_identity_rejects_conflicts(prior, candidate, gap: str) -> None:
    assert release_identity_admission_gaps(candidate, (prior,)) == (gap,)


def test_release_attestation_round_trips_the_canonical_identity() -> None:
    release = _release("0.2.0-alpha.1")
    attestation = accepted_release_attestation(
        release,
        issued_at=datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert accepted_release_identities((attestation,)) == (release,)


def test_release_attestation_rejects_malformed_owned_predicate() -> None:
    release = _release("0.2.0-alpha.1")
    payload = accepted_release_attestation(
        release,
        issued_at=datetime(2026, 8, 25, tzinfo=UTC),
    ).model_dump(mode="json")
    payload["payload"]["body"]["identity"]["wheel_sha256"] = "e" * 64

    malformed = Attestation.issue({key: value for key, value in payload.items() if key != "id"})
    with pytest.raises(ValueError, match="accepted_release_attestation_invalid"):
        accepted_release_identities((malformed,))


def test_package_materialization_rejects_a_symlinked_common_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    common = tmp_path / "common"
    external = tmp_path / "external-packages"
    external.mkdir()
    (common / "ethos").mkdir(parents=True)
    (common / "ethos/packages").symlink_to(external, target_is_directory=True)
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")
    build = build_identity(
        product="0.2.0-alpha.1",
        source_commit="a" * 40,
        source_tree="b" * 40,
        channel="development",
        acceptance_state="unaccepted",
    )
    monkeypatch.setattr(release_transition, "git_common_dir", lambda _root: common.as_posix())
    monkeypatch.setattr(release_transition, "wheel_build_identity", lambda _wheel: build)

    with pytest.raises(ValueError, match="release_package_store_invalid"):
        release_transition.materialize_release_wheel(
            repo,
            wheel,
            expected_build=build,
            collision="collision",
        )

    assert tuple(external.iterdir()) == ()
