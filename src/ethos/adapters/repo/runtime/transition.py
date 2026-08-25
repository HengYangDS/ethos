"""Execute one admitted immutable identity materialization transition."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.repository.release.admission import AcceptedReleaseIdentity
from ethos.repository.release.admission import AcceptedRuntimeIdentity
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import accepted_runtime_attestation
from ethos.repository.release.admission import accepted_runtime_identities
from ethos.repository.release.admission import release_identity_admission_gaps
from ethos.repository.release.admission import runtime_identity_admission_gaps
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import wheel_build_identity

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.contracts.semantic import Attestation


@dataclass(frozen=True, slots=True)
class IdentityTransition[IdentityT]:
    """One immutable identity effect compiled from pure domain predicates."""

    candidate: IdentityT
    prior_identities: Callable[[tuple[Attestation, ...]], tuple[IdentityT, ...]]
    admission_gaps: Callable[[IdentityT, tuple[IdentityT, ...]], tuple[str, ...]]
    materialize: Callable[[], Path]
    post_observe: Callable[[Path], IdentityT]
    issue_attestation: Callable[[IdentityT], Attestation]


@dataclass(frozen=True, slots=True)
class IdentityTransitionResult[IdentityT]:
    """Post-observed artifact and canonical identity selected by a transition."""

    artifact: Path
    identity: IdentityT
    attestation: Attestation


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    """One post-observed wheel in the repository's immutable package store."""

    path: Path
    sha256: str
    build: BuildIdentity
    accepted_identity: AcceptedReleaseIdentity | None


def execute_identity_transition[IdentityT](
    repo: Path,
    transition: IdentityTransition[IdentityT],
) -> IdentityTransitionResult[IdentityT]:
    """Admit, materialize, observe, and attest one immutable identity in order."""
    _root, attestations = read_attestation_set(repo)
    gaps = transition.admission_gaps(
        transition.candidate,
        transition.prior_identities(attestations),
    )
    if gaps:
        raise ValueError(",".join(gaps))

    artifact = transition.materialize()
    observed = transition.post_observe(artifact)
    if observed != transition.candidate:
        message = "identity_transition_post_observation_mismatch"
        raise ValueError(message)

    selected = record_attestation_once(
        repo,
        transition.issue_attestation(observed),
    )
    selected_identities = transition.prior_identities((selected,))
    if selected_identities != (observed,):
        message = "identity_transition_attestation_mismatch"
        raise ValueError(message)
    return IdentityTransitionResult(
        artifact=artifact,
        identity=observed,
        attestation=selected,
    )


def materialize_release_wheel(
    repo: Path,
    wheel: Path,
    *,
    expected_build: BuildIdentity,
    collision: str,
) -> ReleaseArtifact:
    """Admit and materialize one wheel through the sole release-identity transition."""
    payload = wheel.read_bytes()
    sha256 = hashlib.sha256(payload).hexdigest()
    build = wheel_build_identity(wheel)
    if build != expected_build:
        message = "release_wheel_build_identity_stale"
        raise ValueError(message)
    target = Path(git_common_dir(repo)) / "ethos" / "packages" / sha256 / wheel.name
    release = (
        accepted_release_identity(build, wheel_sha256=sha256)
        if build.acceptance_state == "accepted"
        else None
    )

    def materialize() -> Path:
        return write_content_addressed(target, payload, collision=collision)

    if release is None:
        durable = materialize()
        observed_build = wheel_build_identity(durable)
        if observed_build != build or hashlib.sha256(durable.read_bytes()).hexdigest() != sha256:
            message = "identity_transition_post_observation_mismatch"
            raise ValueError(message)
    else:
        result = execute_identity_transition(
            repo,
            IdentityTransition(
                candidate=release,
                prior_identities=accepted_release_identities,
                admission_gaps=release_identity_admission_gaps,
                materialize=materialize,
                post_observe=_observe_release_wheel,
                issue_attestation=lambda identity: accepted_release_attestation(
                    identity,
                    issued_at=datetime.now(UTC),
                ),
            ),
        )
        durable = result.artifact
    return ReleaseArtifact(
        path=durable,
        sha256=sha256,
        build=build,
        accepted_identity=release,
    )


def execute_runtime_identity_transition(
    repo: Path,
    candidate: AcceptedRuntimeIdentity | None,
    *,
    materialize: Callable[[], Path],
    post_observe: Callable[[Path], AcceptedRuntimeIdentity | None],
) -> Path:
    """Materialize a runtime and attest accepted identity only after observation."""
    if candidate is None:
        artifact = materialize()
        if post_observe(artifact) is not None:
            message = "identity_transition_post_observation_mismatch"
            raise ValueError(message)
        return artifact

    def observe_accepted(path: Path) -> AcceptedRuntimeIdentity:
        observed = post_observe(path)
        if observed is None:
            message = "identity_transition_post_observation_mismatch"
            raise ValueError(message)
        return observed

    result = execute_identity_transition(
        repo,
        IdentityTransition(
            candidate=candidate,
            prior_identities=accepted_runtime_identities,
            admission_gaps=runtime_identity_admission_gaps,
            materialize=materialize,
            post_observe=observe_accepted,
            issue_attestation=lambda identity: accepted_runtime_attestation(
                identity,
                issued_at=datetime.now(UTC),
            ),
        ),
    )
    return result.artifact


def require_runtime_identity_attested(
    repo: Path,
    candidate: AcceptedRuntimeIdentity | None,
) -> None:
    """Require exact accepted release and runtime Attestations before activation."""
    if candidate is None:
        return
    _root, attestations = read_attestation_set(repo)
    if candidate.release not in accepted_release_identities(attestations):
        message = "accepted_release_identity_unattested"
        raise ValueError(message)
    if candidate not in accepted_runtime_identities(attestations):
        message = "accepted_runtime_identity_unattested"
        raise ValueError(message)


def _observe_release_wheel(path: Path) -> AcceptedReleaseIdentity:
    build = wheel_build_identity(path)
    return accepted_release_identity(
        build,
        wheel_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
