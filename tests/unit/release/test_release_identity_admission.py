from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest

from ethos.contracts.semantic import Attestation
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import accepted_runtime_attestation
from ethos.repository.release.admission import accepted_runtime_identities
from ethos.repository.release.admission import accepted_runtime_identity
from ethos.repository.release.admission import release_identity_admission_gaps
from ethos.repository.release.admission import release_tag_admission_gaps
from ethos.repository.release.admission import runtime_identity_admission_gaps
from ethos.repository.release.identity import build_identity


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


def test_release_identity_rejects_product_version_rollback() -> None:
    prior = _release("0.2.0-alpha.2")
    candidate = _release("0.2.0-alpha.1", commit="e" * 40, tree="f" * 40)

    assert release_identity_admission_gaps(candidate, (prior,)) == (
        "accepted_version_rollback:0.2.0-alpha.1<0.2.0-alpha.2",
    )


def test_release_identity_rejects_same_version_with_different_source() -> None:
    prior = _release("0.2.0-alpha.1")
    candidate = _release("0.2.0-alpha.1", commit="e" * 40, tree="f" * 40)

    assert release_identity_admission_gaps(candidate, (prior,)) == (
        "accepted_version_source_conflict:0.2.0-alpha.1",
    )


def test_release_identity_rejects_same_source_with_different_artifact() -> None:
    prior = _release("0.2.0-alpha.1")
    candidate = _release("0.2.0-alpha.1", wheel="e" * 64)

    assert release_identity_admission_gaps(candidate, (prior,)) == (
        "accepted_version_artifact_conflict:0.2.0-alpha.1",
    )


def test_runtime_identity_is_unique_within_platform_and_abi() -> None:
    release = _release("0.2.0-alpha.1")
    prior = accepted_runtime_identity(
        release,
        runtime_digest="d" * 64,
        python_abi="cpython-314",
        platform="darwin",
    )
    conflicting = accepted_runtime_identity(
        release,
        runtime_digest="e" * 64,
        python_abi="cpython-314",
        platform="darwin",
    )
    linux = accepted_runtime_identity(
        release,
        runtime_digest="f" * 64,
        python_abi="cpython-314",
        platform="linux",
    )

    assert runtime_identity_admission_gaps(prior, (prior,)) == ()
    assert runtime_identity_admission_gaps(conflicting, (prior,)) == (
        "accepted_runtime_artifact_conflict:0.2.0-alpha.1:darwin:cpython-314",
    )
    assert runtime_identity_admission_gaps(linux, (prior,)) == ()


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


def test_runtime_attestation_round_trips_platform_qualified_identity() -> None:
    runtime = accepted_runtime_identity(
        _release("0.2.0-alpha.1"),
        runtime_digest="d" * 64,
        python_abi="cpython-314",
        platform="darwin",
    )
    attestation = accepted_runtime_attestation(
        runtime,
        issued_at=datetime(2026, 8, 25, tzinfo=UTC),
    )

    assert accepted_runtime_identities((attestation,)) == (runtime,)


def test_release_tag_must_project_the_exact_version_and_source() -> None:
    candidate = _release("0.2.0-alpha.1")

    assert (
        release_tag_admission_gaps(
            candidate,
            tag_name="v0.2.0-alpha.1",
            tag_object_oid="1" * 40,
            peeled_commit=candidate.build.source_commit,
            tree_oid=candidate.build.source_tree,
        )
        == ()
    )
    assert release_tag_admission_gaps(
        candidate,
        tag_name="v0.2.0-alpha.2",
        tag_object_oid="1" * 40,
        peeled_commit="2" * 40,
        tree_oid="3" * 40,
    ) == (
        "release_tag_version_mismatch:v0.2.0-alpha.2",
        "release_tag_source_mismatch:v0.2.0-alpha.1",
        "release_tag_tree_mismatch:v0.2.0-alpha.1",
    )
