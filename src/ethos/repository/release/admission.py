"""Admit immutable accepted release and runtime identities."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from packaging.version import Version

from ethos.contracts.digest import is_sha256_hex
from ethos.contracts.semantic import Attestation
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import build_identity_from_projection

if TYPE_CHECKING:
    from datetime import datetime

_RELEASE = "release:accepted-identity"
_RELEASE_BUILD_INVALID = "accepted_release_build_identity_invalid"
_RELEASE_PROJECTION_INVALID = "accepted_release_identity_projection_invalid"
_RELEASE_ATTESTATION_INVALID = "accepted_release_attestation_invalid"
_RELEASE_WHEEL_INVALID = "accepted_release_wheel_identity_invalid"
_RELEASE_ARTIFACTS_INVALID = "accepted_release_artifacts_invalid"
_RELEASE_CHECKSUMS_INVALID = "accepted_release_checksums_invalid"
_BOUND_KEYS = ("checksums_sha256", "artifacts")


class AcceptedReleaseIdentity(NamedTuple):
    """One accepted product/source/artifact identity.

    A bound identity also carries the digest of the release's attested checksum file and the
    name and digest of every wheel and archive that file lists; an earlier one carries neither.
    """

    build: BuildIdentity
    wheel_sha256: str
    checksums_sha256: str = ""
    artifacts: tuple[tuple[str, str], ...] = ()

    def projection(self) -> dict[str, object]:
        earlier: dict[str, object] = {**self.build.projection(), "wheel_sha256": self.wheel_sha256}
        if not self.artifacts:
            return earlier
        bound = {"checksums_sha256": self.checksums_sha256, "artifacts": dict(self.artifacts)}
        return {**earlier, "schema_version": 3, **bound}


def accepted_release_identity(
    build: BuildIdentity,
    *,
    wheel_sha256: str,
    checksums_sha256: str = "",
    artifacts: Mapping[str, str] | None = None,
) -> AcceptedReleaseIdentity:
    if Version(build.distribution_version).dev is not None:
        raise ValueError(_RELEASE_BUILD_INVALID)
    if not is_sha256_hex(wheel_sha256):
        raise ValueError(_RELEASE_WHEEL_INVALID)
    named = dict(artifacts or {})
    # The accepted wheel is one of the published files, so a bound identity names it.
    if (checksums_sha256 or named) and not (
        all(map(is_sha256_hex, (checksums_sha256, *named.values())))
        and wheel_sha256 in named.values()
    ):
        raise ValueError(_RELEASE_ARTIFACTS_INVALID)
    return AcceptedReleaseIdentity(
        build, wheel_sha256, checksums_sha256, tuple(sorted(named.items()))
    )


def checksum_bound_release(
    release: AcceptedReleaseIdentity, checksums: bytes, *, published: Mapping[str, str]
) -> AcceptedReleaseIdentity:
    """Bind a release to its checksum file and to every wheel and archive that file lists.

    `published` holds the digest the caller observed for each published file it read, by name;
    one that the checksum file does not list with that digest refuses the binding.
    """
    lines = checksums.decode("ascii", "replace").splitlines()
    # A line that is not `<digest>  <name>` in ASCII, or that repeats a name, is not counted.
    listed = dict(line.split("  ", 1)[::-1] for line in lines if "  " in line and line.isascii())
    if len(listed) != len(lines):
        raise ValueError(_RELEASE_CHECKSUMS_INVALID)
    for name in sorted(published):
        if listed.get(name) != published[name]:
            message = f"accepted_release_checksum_mismatch:{name}"
            raise ValueError(message)
    return accepted_release_identity(
        release.build,
        wheel_sha256=release.wheel_sha256,
        checksums_sha256=hashlib.sha256(checksums).hexdigest(),
        artifacts={name: listed[name] for name in listed if name.endswith((".whl", ".tar.gz"))},
    )


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
        sums = {existing.checksums_sha256, candidate.checksums_sha256} - {""}
        if existing.wheel_sha256 != candidate.wheel_sha256 or len(sums) > 1:
            return (f"accepted_version_artifact_conflict:{candidate.build.product_version}",)
    return ()


def accepted_release_attestation(
    release: AcceptedReleaseIdentity, *, issued_at: datetime
) -> Attestation:
    return _release_attestation(
        release,
        issued_at=issued_at,
        identity_projection=release.projection(),
    )


def _release_attestation(
    release: AcceptedReleaseIdentity,
    *,
    issued_at: datetime,
    identity_projection: Mapping[str, object],
) -> Attestation:
    evidence = (
        f"git:commit:{release.build.source_commit}",
        f"git:tree:{release.build.source_tree}",
        f"sha256:{release.wheel_sha256}",
        *((f"sha256:{release.checksums_sha256}",) if release.checksums_sha256 else ()),
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
            "payload": {"kind": _RELEASE, "body": {"identity": dict(identity_projection)}},
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
        expected = _release_attestation(
            value,
            issued_at=attestation.issued_at,
            identity_projection=raw,
        )
        if expected.model_dump(exclude={"id", "issued_at"}) != attestation.model_dump(
            exclude={"id", "issued_at"}
        ):
            raise ValueError(_RELEASE_ATTESTATION_INVALID)
        values.append(value)
    return tuple(dict.fromkeys(values))


def _release_from_projection(raw: Mapping[object, object]) -> AcceptedReleaseIdentity:
    bound: dict[str, Any] = {}
    if raw.get("schema_version") == 1:
        build = _legacy_release_build(raw)
    else:
        fields = {key: raw[key] for key in raw if key not in {"wheel_sha256", *_BOUND_KEYS}}
        # Version 3 is the version 2 build fields with the checksum binding beside them.
        if fields.get("schema_version") == 3:
            fields["schema_version"] = 2
            bound = {key: raw[key] for key in _BOUND_KEYS}
        build = build_identity_from_projection(fields)
    release = accepted_release_identity(build, wheel_sha256=str(raw["wheel_sha256"]), **bound)
    expected = (
        {
            **release.projection(),
            "schema_version": 1,
            "channel": "accepted",
            "acceptance_state": "accepted",
        }
        if raw.get("schema_version") == 1
        else release.projection()
    )
    if dict(raw) != expected:
        raise ValueError(_RELEASE_PROJECTION_INVALID)
    return release


def _legacy_release_build(raw: Mapping[object, object]) -> BuildIdentity:
    if raw.get("channel") != "accepted" or raw.get("acceptance_state") != "accepted":
        raise ValueError(_RELEASE_PROJECTION_INVALID)
    build = build_identity(
        product=str(raw["product_version"]),
        source_commit=str(raw["source_commit"]),
        source_tree=str(raw["source_tree"]),
        release=True,
    )
    if raw.get("distribution_version") != build.distribution_version:
        raise ValueError(_RELEASE_PROJECTION_INVALID)
    return build
