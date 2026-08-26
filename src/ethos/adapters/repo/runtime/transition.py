"""Execute admitted immutable release and runtime identity transitions."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import NamedTuple
from typing import NoReturn

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.repository.release.admission import AcceptedReleaseIdentity
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import release_identity_admission_gaps
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import wheel_build_identity


class ReleaseArtifact(NamedTuple):
    """Post-observed wheel and its immutable identity."""

    path: Path
    sha256: str
    build: BuildIdentity


def _fail(reason: str) -> NoReturn:
    raise ValueError(reason)


def materialize_release_wheel(
    repo: Path,
    wheel: Path,
    *,
    expected_build: BuildIdentity,
    collision: str,
) -> ReleaseArtifact:
    """Admit and materialize one wheel through the release identity."""
    payload = wheel.read_bytes()
    sha256 = hashlib.sha256(payload).hexdigest()
    build = wheel_build_identity(wheel)
    if build != expected_build:
        _fail("release_wheel_build_identity_stale")
    common = Path(git_common_dir(repo))
    package_store = common / "ethos" / "packages"
    _require_package_store(common, package_store)
    target = package_store / sha256 / wheel.name
    release = (
        accepted_release_identity(build, wheel_sha256=sha256)
        if build.acceptance_state == "accepted"
        else None
    )
    if release:
        _root, attestations = read_attestation_set(repo)
        if gaps := release_identity_admission_gaps(
            release, accepted_release_identities(attestations)
        ):
            raise ValueError(",".join(gaps))
    durable = write_content_addressed(target, payload, collision=collision)
    if release is None:
        if wheel_build_identity(durable) != build or _sha256(durable) != sha256:
            _fail("identity_transition_post_observation_mismatch")
    else:
        observed = _observe_release_wheel(durable)
        if observed != release:
            _fail("identity_transition_post_observation_mismatch")
        recorded = record_attestation_once(
            repo,
            accepted_release_attestation(observed, issued_at=datetime.now(UTC)),
        )
        if accepted_release_identities((recorded,)) != (observed,):
            _fail("identity_transition_attestation_mismatch")
    return ReleaseArtifact(target, sha256, build)


def require_release_identity_attested(
    repo: Path, candidate: AcceptedReleaseIdentity | None
) -> None:
    """Require accepted package provenance before activating its runtime projection."""
    if not candidate:
        return
    _root, attestations = read_attestation_set(repo)
    if candidate not in accepted_release_identities(attestations):
        _fail("accepted_release_identity_unattested")


def _observe_release_wheel(path: Path) -> AcceptedReleaseIdentity:
    return accepted_release_identity(wheel_build_identity(path), wheel_sha256=_sha256(path))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_package_store(common: Path, store: Path) -> None:
    try:
        common_root = common.resolve(strict=True)
        current = store
        while current != common_root:
            if current.is_symlink():
                _fail("release_package_store_invalid")
            current = current.parent
        if current != common_root or common.is_symlink():
            _fail("release_package_store_invalid")
    except (OSError, RuntimeError, ValueError) as error:
        if str(error) == "release_package_store_invalid":
            raise
        message = "release_package_store_invalid"
        raise ValueError(message) from error
