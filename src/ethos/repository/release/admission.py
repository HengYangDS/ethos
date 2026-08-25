"""Admit one immutable accepted release identity against prior facts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import NamedTuple

from packaging.version import Version

from ethos.contracts.semantic import Attestation
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import pep440_product_version

if TYPE_CHECKING:
    from datetime import datetime

_HEX = frozenset("0123456789abcdef")
_RELEASE_PREDICATE = "release:accepted-identity"
_RUNTIME_PREDICATE = "release:accepted-runtime"


class AcceptedReleaseIdentity(NamedTuple):
    """One accepted product/source/artifact/runtime identity."""

    build: BuildIdentity
    wheel_sha256: str

    def projection(self) -> dict[str, str | int]:
        """Return the canonical release-identity projection."""
        return {
            "schema_version": 1,
            **{
                key: value
                for key, value in self.build.projection().items()
                if key != "schema_version"
            },
            "wheel_sha256": self.wheel_sha256,
        }


class AcceptedRuntimeIdentity(NamedTuple):
    """One platform-qualified runtime projection of an accepted release."""

    release: AcceptedReleaseIdentity
    runtime_digest: str
    python_abi: str
    platform: str


def accepted_release_identity(
    build: BuildIdentity,
    *,
    wheel_sha256: str,
) -> AcceptedReleaseIdentity:
    """Validate and compose one accepted release identity."""
    if build.acceptance_state != "accepted" or build.channel != "accepted":
        message = "accepted_release_build_identity_invalid"
        raise ValueError(message)
    if not _valid_digest(wheel_sha256):
        message = "accepted_release_wheel_identity_invalid"
        raise ValueError(message)
    return AcceptedReleaseIdentity(
        build=build,
        wheel_sha256=wheel_sha256,
    )


def accepted_runtime_identity(
    release: AcceptedReleaseIdentity,
    *,
    runtime_digest: str,
    python_abi: str,
    platform: str,
) -> AcceptedRuntimeIdentity:
    """Validate and compose one platform-qualified accepted runtime identity."""
    if not _valid_digest(runtime_digest):
        message = "accepted_release_runtime_identity_invalid"
        raise ValueError(message)
    if not python_abi or not platform:
        message = "accepted_release_runtime_coordinates_invalid"
        raise ValueError(message)
    return AcceptedRuntimeIdentity(
        release=release,
        runtime_digest=runtime_digest,
        python_abi=python_abi,
        platform=platform,
    )


def accepted_release_candidate(
    build: BuildIdentity,
    *,
    wheel_sha256: str,
) -> AcceptedReleaseIdentity | None:
    """Return an accepted release identity only for an accepted build."""
    if build.acceptance_state != "accepted":
        return None
    return accepted_release_identity(build, wheel_sha256=wheel_sha256)


def accepted_runtime_candidate(
    release: AcceptedReleaseIdentity | None,
    *,
    runtime_digest: str,
    python_abi: str,
    platform: str,
) -> AcceptedRuntimeIdentity | None:
    """Return a runtime identity only when an accepted release exists."""
    if release is None:
        return None
    return accepted_runtime_identity(
        release,
        runtime_digest=runtime_digest,
        python_abi=python_abi,
        platform=platform,
    )


def release_identity_admission_gaps(
    candidate: AcceptedReleaseIdentity,
    prior: tuple[AcceptedReleaseIdentity, ...],
) -> tuple[str, ...]:
    """Reject accepted-version rollback or immutable identity reuse."""
    candidate_version = Version(pep440_product_version(candidate.build.product_version))
    prior_versions = tuple(
        Version(pep440_product_version(item.build.product_version)) for item in prior
    )
    if prior_versions and candidate_version < max(prior_versions):
        latest = max(prior_versions)
        return (
            (
                "accepted_version_rollback:"
                f"{candidate.build.product_version}<{_product_version(prior, latest)}"
            ),
        )
    for existing in prior:
        if existing.build.product_version != candidate.build.product_version:
            continue
        if (
            existing.build.source_commit != candidate.build.source_commit
            or existing.build.source_tree != candidate.build.source_tree
        ):
            return (f"accepted_version_source_conflict:{candidate.build.product_version}",)
        if existing.wheel_sha256 != candidate.wheel_sha256:
            return (f"accepted_version_artifact_conflict:{candidate.build.product_version}",)
    return ()


def runtime_identity_admission_gaps(
    candidate: AcceptedRuntimeIdentity,
    prior: tuple[AcceptedRuntimeIdentity, ...],
) -> tuple[str, ...]:
    """Reject two runtime byte identities for one release/platform/ABI tuple."""
    for existing in prior:
        if (
            existing.release == candidate.release
            and existing.platform == candidate.platform
            and existing.python_abi == candidate.python_abi
            and existing.runtime_digest != candidate.runtime_digest
        ):
            return (
                (
                    "accepted_runtime_artifact_conflict:"
                    f"{candidate.release.build.product_version}:"
                    f"{candidate.platform}:{candidate.python_abi}"
                ),
            )
    return ()


def accepted_release_attestation(
    release: AcceptedReleaseIdentity,
    *,
    issued_at: datetime,
) -> Attestation:
    """Issue one immutable accepted-release identity fact."""
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": _RELEASE_PREDICATE,
            "verifier": "ethos:release-identity-admission",
            "subject": f"release:ethos:{release.build.product_version}",
            "issued_at": issued_at,
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": _RELEASE_PREDICATE,
                "body": {"identity": release.projection()},
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": _release_evidence_refs(release),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": release.wheel_sha256,
            "mints_authority": False,
        }
    )


def accepted_release_identities(
    attestations: tuple[Attestation, ...],
) -> tuple[AcceptedReleaseIdentity, ...]:
    """Read accepted release identities from the canonical Attestation set."""
    releases = tuple(
        _release_from_attestation(attestation)
        for attestation in attestations
        if attestation.predicate == _RELEASE_PREDICATE
    )
    return tuple(
        sorted(
            dict.fromkeys(releases),
            key=lambda item: (
                Version(pep440_product_version(item.build.product_version)),
                item.build.source_commit,
                item.wheel_sha256,
            ),
        )
    )


def accepted_runtime_attestation(
    runtime: AcceptedRuntimeIdentity,
    *,
    issued_at: datetime,
) -> Attestation:
    """Issue one immutable platform-qualified runtime identity fact."""
    projection = _runtime_projection(runtime)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": _RUNTIME_PREDICATE,
            "verifier": "ethos:release-identity-admission",
            "subject": (
                f"runtime:ethos:{runtime.release.build.product_version}:"
                f"{runtime.platform}:{runtime.python_abi}"
            ),
            "issued_at": issued_at,
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": _RUNTIME_PREDICATE,
                "body": {"identity": projection},
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": _runtime_evidence_refs(runtime),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": runtime.runtime_digest,
            "mints_authority": False,
        }
    )


def accepted_runtime_identities(
    attestations: tuple[Attestation, ...],
) -> tuple[AcceptedRuntimeIdentity, ...]:
    """Read platform-qualified runtime identities from Attestations."""
    runtimes = tuple(
        _runtime_from_attestation(attestation)
        for attestation in attestations
        if attestation.predicate == _RUNTIME_PREDICATE
    )
    return tuple(
        sorted(
            dict.fromkeys(runtimes),
            key=lambda item: (
                Version(pep440_product_version(item.release.build.product_version)),
                item.platform,
                item.python_abi,
                item.runtime_digest,
            ),
        )
    )


def release_tag_admission_gaps(
    release: AcceptedReleaseIdentity,
    *,
    tag_name: str,
    tag_object_oid: str,
    peeled_commit: str,
    tree_oid: str,
) -> tuple[str, ...]:
    """Validate one annotated-tag projection of an accepted release fact."""
    expected = f"v{release.build.product_version}"
    gaps: list[str] = []
    if tag_name != expected:
        gaps.append(f"release_tag_version_mismatch:{tag_name}")
    if not _valid_git_identity(tag_object_oid):
        gaps.append(f"release_tag_object_invalid:{tag_name}")
    if peeled_commit != release.build.source_commit:
        gaps.append(f"release_tag_source_mismatch:{expected}")
    if tree_oid != release.build.source_tree:
        gaps.append(f"release_tag_tree_mismatch:{expected}")
    return tuple(gaps)


def _product_version(releases: tuple[AcceptedReleaseIdentity, ...], version: Version) -> str:
    return next(
        item.build.product_version
        for item in releases
        if Version(pep440_product_version(item.build.product_version)) == version
    )


def _release_from_attestation(attestation: Attestation) -> AcceptedReleaseIdentity:
    try:
        raw = attestation.payload.body["identity"]
        _require(valid=isinstance(raw, Mapping) and raw.get("schema_version") == 1)
        release = _release_from_projection(raw)
        _require(
            valid=raw == release.projection()
            and attestation.payload.kind == _RELEASE_PREDICATE
            and attestation.subject == f"release:ethos:{release.build.product_version}"
            and attestation.verdict == "pass"
            and attestation.effect_digest == release.wheel_sha256
            and attestation.evidence_refs == _release_evidence_refs(release)
        )
    except (KeyError, TypeError, ValueError) as error:
        message = "accepted_release_attestation_invalid"
        raise ValueError(message) from error
    else:
        return release


def _release_evidence_refs(release: AcceptedReleaseIdentity) -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                f"git:commit:{release.build.source_commit}",
                f"git:tree:{release.build.source_tree}",
                f"sha256:{release.wheel_sha256}",
            )
        )
    )


def _runtime_projection(runtime: AcceptedRuntimeIdentity) -> dict[str, object]:
    return {
        "schema_version": 1,
        "release": runtime.release.projection(),
        "runtime_digest": runtime.runtime_digest,
        "python_abi": runtime.python_abi,
        "platform": runtime.platform,
    }


def _runtime_from_attestation(attestation: Attestation) -> AcceptedRuntimeIdentity:
    try:
        raw = attestation.payload.body["identity"]
        _require(valid=isinstance(raw, Mapping) and raw.get("schema_version") == 1)
        release_raw = raw["release"]
        _require(valid=isinstance(release_raw, Mapping))
        release = _release_from_projection(release_raw)
        runtime = accepted_runtime_identity(
            release,
            runtime_digest=str(raw["runtime_digest"]),
            python_abi=str(raw["python_abi"]),
            platform=str(raw["platform"]),
        )
        expected_subject = (
            f"runtime:ethos:{release.build.product_version}:{runtime.platform}:{runtime.python_abi}"
        )
        _require(
            valid=raw == _runtime_projection(runtime)
            and attestation.payload.kind == _RUNTIME_PREDICATE
            and attestation.subject == expected_subject
            and attestation.verdict == "pass"
            and attestation.effect_digest == runtime.runtime_digest
            and attestation.evidence_refs == _runtime_evidence_refs(runtime)
        )
    except (IndexError, KeyError, TypeError, ValueError) as error:
        message = "accepted_runtime_attestation_invalid"
        raise ValueError(message) from error
    else:
        return runtime


def _release_from_projection(raw: Mapping[object, object]) -> AcceptedReleaseIdentity:
    build = build_identity(
        product=str(raw["product_version"]),
        source_commit=str(raw["source_commit"]),
        source_tree=str(raw["source_tree"]),
        channel="accepted",
        acceptance_state="accepted",
    )
    release = accepted_release_identity(build, wheel_sha256=str(raw["wheel_sha256"]))
    if raw != release.projection():
        message = "accepted_release_identity_projection_invalid"
        raise ValueError(message)
    return release


def _runtime_evidence_refs(runtime: AcceptedRuntimeIdentity) -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                *_release_evidence_refs(runtime.release),
                f"runtime:sha256:{runtime.runtime_digest}",
            )
        )
    )


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and not set(value) - _HEX


def _valid_git_identity(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - _HEX


def _require(*, valid: bool) -> None:
    if not valid:
        message = "release_identity_projection_invalid"
        raise ValueError(message)
