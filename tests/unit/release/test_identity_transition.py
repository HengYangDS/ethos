from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.runtime.transition import IdentityTransition
from ethos.adapters.repo.runtime.transition import execute_identity_transition
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import release_identity_admission_gaps
from ethos.repository.release.identity import build_identity

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *arguments: str) -> None:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def _repository(root: Path) -> Path:
    root.mkdir()
    _git(root, "init", "--quiet", "--initial-branch=dev")
    return root


def _release(*, commit: str = "a" * 40, tree: str = "b" * 40):
    return accepted_release_identity(
        build_identity(
            product="0.2.0-alpha.1",
            source_commit=commit,
            source_tree=tree,
            channel="accepted",
            acceptance_state="accepted",
        ),
        wheel_sha256="c" * 64,
    )


def _transition(candidate, *, materialize, observe):
    return IdentityTransition(
        candidate=candidate,
        prior_identities=accepted_release_identities,
        admission_gaps=release_identity_admission_gaps,
        materialize=materialize,
        post_observe=observe,
        issue_attestation=lambda identity: accepted_release_attestation(
            identity,
            issued_at=datetime(2026, 8, 25, tzinfo=UTC),
        ),
    )


def test_identity_transition_rejects_conflict_before_artifact_effect(tmp_path: Path) -> None:
    repo = _repository(tmp_path / "repo")
    prior = _release()
    candidate = _release(commit="d" * 40, tree="e" * 40)
    record_attestations(
        repo,
        (
            accepted_release_attestation(
                prior,
                issued_at=datetime(2026, 8, 24, tzinfo=UTC),
            ),
        ),
    )
    effects: list[str] = []

    with pytest.raises(ValueError, match="accepted_version_source_conflict"):
        execute_identity_transition(
            repo,
            _transition(
                candidate,
                materialize=lambda: effects.append("materialize") or tmp_path / "artifact",
                observe=lambda _path: candidate,
            ),
        )

    assert effects == []
    _root, attestations = read_attestation_set(repo)
    assert accepted_release_identities(attestations) == (prior,)


def test_identity_transition_orders_effect_observation_and_attestation(tmp_path: Path) -> None:
    repo = _repository(tmp_path / "repo")
    candidate = _release()
    artifact = tmp_path / "artifact"
    events: list[str] = []

    def materialize() -> Path:
        events.append("materialize")
        artifact.write_bytes(b"artifact")
        return artifact

    def observe(path: Path):
        assert path == artifact
        assert path.read_bytes() == b"artifact"
        events.append("post-observe")
        return candidate

    result = execute_identity_transition(
        repo,
        _transition(candidate, materialize=materialize, observe=observe),
    )

    assert result.identity == candidate
    assert result.artifact == artifact
    assert events == ["materialize", "post-observe"]
    _root, attestations = read_attestation_set(repo)
    assert accepted_release_identities(attestations) == (candidate,)


def test_identity_transition_does_not_attest_failed_post_observation(tmp_path: Path) -> None:
    repo = _repository(tmp_path / "repo")
    candidate = _release()
    artifact = tmp_path / "artifact"

    def materialize() -> Path:
        artifact.write_bytes(b"artifact")
        return artifact

    with pytest.raises(ValueError, match="identity_transition_post_observation_mismatch"):
        execute_identity_transition(
            repo,
            _transition(
                candidate,
                materialize=materialize,
                observe=lambda _path: _release(commit="d" * 40, tree="e" * 40),
            ),
        )

    assert artifact.read_bytes() == b"artifact"
    _root, attestations = read_attestation_set(repo)
    assert accepted_release_identities(attestations) == ()
