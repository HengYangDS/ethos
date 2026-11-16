"""Execute admitted immutable release and runtime identity transitions."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.digest import file_sha256
from ethos.contracts.outcome import refuse
from ethos.repository.release.admission import AcceptedReleaseIdentity
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import checksum_bound_release
from ethos.repository.release.admission import identities_agree
from ethos.repository.release.admission import release_identity_admission_gaps
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import wheel_build_identity


class PackageArtifact(NamedTuple):
    """Post-observed wheel and its immutable identity."""

    path: Path
    sha256: str
    build: BuildIdentity


def materialize_package_wheel(
    repo: Path,
    wheel: Path,
    *,
    expected_build: BuildIdentity,
    collision: str,
) -> PackageArtifact:
    """Materialize one exact wheel without implying package release."""
    payload = wheel.read_bytes()
    sha256 = hashlib.sha256(payload).hexdigest()
    build = wheel_build_identity(wheel)
    if build != expected_build:
        refuse("release_wheel_build_identity_stale")
    common = Path(git_common_dir(repo))
    package_store = common / "ethos" / "packages"
    _require_package_store(common, package_store)
    target = package_store / sha256 / wheel.name
    durable = write_content_addressed(target, payload, collision=collision)
    if wheel_build_identity(durable) != build or file_sha256(durable) != sha256:
        refuse("identity_transition_post_observation_mismatch")
    return PackageArtifact(target, sha256, build)


def admit_explicit_release(
    repo: Path, wheel: Path, *, expected_build: BuildIdentity, checksums: Path | None = None
) -> tuple[AcceptedReleaseIdentity, bool]:
    """Admit one explicit release before any effect, and say whether the set already holds it.

    With the release's checksum file, the identity binds it and every wheel and archive it lists.
    A version keeps the identity it first recorded: for a later transition of the same source and
    wheel, with the binding or without it, the answer is that identity, and the set holds it.
    """
    return _admitted(repo, wheel, file_sha256(wheel), expected_build, checksums)


def _admitted(
    repo: Path, wheel: Path, sha256: str, expected_build: BuildIdentity, checksums: Path | None
) -> tuple[AcceptedReleaseIdentity, bool]:
    """Admit the wheel by the digest of its bytes, which a caller that stores them read once."""
    build = wheel_build_identity(wheel)
    if build != expected_build:
        refuse("release_wheel_build_identity_stale")
    release = accepted_release_identity(build, wheel_sha256=sha256)
    if checksums is not None:
        release = checksum_bound_release(
            release, checksums.read_bytes(), published={wheel.name: sha256}
        )
    _root, attestations = read_attestation_set(repo)
    accepted = accepted_release_identities(attestations)
    if gaps := release_identity_admission_gaps(release, accepted):
        refuse(*gaps)
    # The version's identity is a record of the same build that agrees with this candidate: it
    # equals it, or differs only in a checksum binding that one of the two lacks. The rule is
    # admission's own, applied here too, so that no other record is ever answered.
    agreed = (item for item in accepted if item.build == release.build)
    recorded = next((item for item in agreed if identities_agree(item, release)), None)
    return recorded or release, recorded is not None


def materialize_explicit_release(
    repo: Path,
    wheel: Path,
    *,
    expected_build: BuildIdentity,
    collision: str,
    checksums: Path | None = None,
) -> AcceptedReleaseIdentity:
    """Admit, materialize, observe, and attest one explicit release."""
    # The wheel is read once: the bytes that admission hashes are the bytes the store receives.
    payload = wheel.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    release, _held = _admitted(repo, wheel, digest, expected_build, checksums)
    common = Path(git_common_dir(repo))
    package_store = common / "ethos" / "packages"
    _require_package_store(common, package_store)
    target = package_store / release.wheel_sha256 / wheel.name
    durable = write_content_addressed(target, payload, collision=collision)
    # The effect is the stored wheel, so the fresh observation covers the build and that wheel.
    if _observe_release_wheel(durable)[:2] != release[:2]:
        refuse("identity_transition_post_observation_mismatch")
    recorded = record_attestation_once(
        repo,
        accepted_release_attestation(release, issued_at=datetime.now(UTC)),
    )
    # Admission named the identity that stands, so a record that another writer made since
    # is not this transition's, whatever it binds.
    if accepted_release_identities((recorded,)) != (release,):
        refuse("identity_transition_attestation_mismatch")
    return release


def _observe_release_wheel(path: Path) -> AcceptedReleaseIdentity:
    return accepted_release_identity(wheel_build_identity(path), wheel_sha256=file_sha256(path))


def _require_package_store(common: Path, store: Path) -> None:
    try:
        common_root = common.resolve(strict=True)
        current = store
        while current != common_root:
            if current.is_symlink():
                refuse("release_package_store_invalid")
            current = current.parent
        if current != common_root or common.is_symlink():
            refuse("release_package_store_invalid")
    except (OSError, RuntimeError, ValueError) as error:
        if str(error) == "release_package_store_invalid":
            raise
        message = "release_package_store_invalid"
        raise ValueError(message) from error
