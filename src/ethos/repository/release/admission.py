"""Admit immutable accepted release and runtime identities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import NamedTuple

from packaging.version import Version

from ethos.contracts.semantic import Attestation
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity_from_projection

if TYPE_CHECKING:
    from datetime import datetime

_HEX = frozenset("0123456789abcdef")
_RELEASE = "release:accepted-identity"
_RELEASE_BUILD_INVALID = "accepted_release_build_identity_invalid"
_RELEASE_PROJECTION_INVALID = "accepted_release_identity_projection_invalid"
_RELEASE_ATTESTATION_INVALID = "accepted_release_attestation_invalid"
_RELEASE_WHEEL_INVALID = "accepted_release_wheel_identity_invalid"


class AcceptedReleaseIdentity(NamedTuple):
    """One accepted product/source/artifact identity."""

    build: BuildIdentity
    wheel_sha256: str

    def projection(self) -> dict[str, object]:
        return {
            **self.build.projection(),
            "wheel_sha256": self.wheel_sha256,
        }


def accepted_release_identity(
    build: BuildIdentity, *, wheel_sha256: str
) -> AcceptedReleaseIdentity:
    if build[4:] != ("accepted", "accepted"):
        raise ValueError(_RELEASE_BUILD_INVALID)
    if len(wheel_sha256) != 64 or set(wheel_sha256) - _HEX:
        raise ValueError(_RELEASE_WHEEL_INVALID)
    return AcceptedReleaseIdentity(build, wheel_sha256)


def release_identity_admission_gaps(
    candidate: AcceptedReleaseIdentity,
    prior: tuple[AcceptedReleaseIdentity, ...],
) -> tuple[str, ...]:
    version = Version(candidate.build.distribution_version)
    previous = {
        Version(item.build.distribution_version): item.build.product_version for item in prior
    }
    if previous and version < max(previous):
        latest = previous[max(previous)]
        return (f"accepted_version_rollback:{candidate.build.product_version}<{latest}",)
    for existing in prior:
        if existing.build.product_version != candidate.build.product_version:
            continue
        if existing.build[2:4] != candidate.build[2:4]:
            return (f"accepted_version_source_conflict:{candidate.build.product_version}",)
        if existing.wheel_sha256 != candidate.wheel_sha256:
            return (f"accepted_version_artifact_conflict:{candidate.build.product_version}",)
    return ()


def accepted_release_attestation(
    release: AcceptedReleaseIdentity, *, issued_at: datetime
) -> Attestation:
    evidence = (
        f"git:commit:{release.build.source_commit}",
        f"git:tree:{release.build.source_tree}",
        f"sha256:{release.wheel_sha256}",
    )
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": _RELEASE,
            "verifier": "ethos:release-identity-admission",
            "subject": f"release:ethos:{release.build.product_version}",
            "issued_at": issued_at,
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": _RELEASE, "body": {"identity": release.projection()}},
            "relations": (),
            "advisories": (),
            "evidence_refs": tuple(sorted(evidence)),
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
    values = []
    for attestation in attestations:
        if attestation.predicate != _RELEASE:
            continue
        raw = attestation.payload.body.get("identity")
        if not isinstance(raw, Mapping):
            raise TypeError(_RELEASE_ATTESTATION_INVALID)
        try:
            value = _release_from_projection(raw)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(_RELEASE_ATTESTATION_INVALID) from error
        expected = accepted_release_attestation(value, issued_at=attestation.issued_at)
        if expected.model_dump(exclude={"id", "issued_at"}) != attestation.model_dump(
            exclude={"id", "issued_at"}
        ):
            raise ValueError(_RELEASE_ATTESTATION_INVALID)
        values.append(value)
    return tuple(dict.fromkeys(values))


def _release_from_projection(raw: Mapping[object, object]) -> AcceptedReleaseIdentity:
    build = build_identity_from_projection(
        {key: value for key, value in raw.items() if key != "wheel_sha256"}
    )
    release = accepted_release_identity(build, wheel_sha256=str(raw["wheel_sha256"]))
    if dict(raw) != release.projection():
        raise ValueError(_RELEASE_PROJECTION_INVALID)
    return release
