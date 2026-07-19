"""Typed carrier contracts for Budget Contract v2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal
from typing import NoReturn
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

if TYPE_CHECKING:
    from collections.abc import Iterable

NonEmptyStr = Annotated[str, Field(min_length=1)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"

CarrierRole = Literal[
    "authored_behavioral_source",
    "authored_declarative_source",
    "template_source",
    "test_source",
    "derived_projection",
    "evidence_instance",
    "governance_history",
    "documentation",
    "vendor_or_lock",
    "runtime_local",
]
CarrierDisposition = Literal["measure", "exclude"]
CarrierState = Literal[
    "classified",
    "excluded",
    "unclassified",
    "ambiguous",
    "unsupported",
]


def _raise_contract_error(message: str) -> NoReturn:
    """Raise one stable carrier-contract validation error."""
    raise ValueError(message)


class CarrierIdentity(BaseModel):
    """One immutable path classifier and its Budget Contract v2 identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    carrier_id: NonEmptyStr
    role: CarrierRole
    scope_id: NonEmptyStr
    disposition: CarrierDisposition
    metric_profile: NonEmptyStr | None = None
    extensions: tuple[str, ...] = ()
    include: tuple[NonEmptyStr, ...] = Field(min_length=1)
    exclude: tuple[NonEmptyStr, ...] = ()
    owner: NonEmptyStr
    exclusion_reason: NonEmptyStr | None = None

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Require unique lowercase dotted extensions."""
        if len(values) != len(set(values)):
            _raise_contract_error("carrier extensions must be unique")
        for value in values:
            if (
                not value.startswith(".")
                or value != value.lower()
                or "/" in value
                or "\\" in value
                or len(value) == 1
            ):
                _raise_contract_error("carrier extensions must be lowercase dotted suffixes")
        return values

    @field_validator("include", "exclude")
    @classmethod
    def validate_matchers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Require unique repository-relative POSIX matchers."""
        if len(values) != len(set(values)):
            _raise_contract_error("carrier path matchers must be unique")
        for value in values:
            path = PurePosixPath(value)
            if (
                path.is_absolute()
                or value.startswith("./")
                or "\\" in value
                or ".." in path.parts
                or "\x00" in value
            ):
                _raise_contract_error(
                    "carrier path matchers must be repository-relative POSIX paths"
                )
        return values

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        """Bind measured and excluded identities to disjoint required fields."""
        if self.disposition == "measure":
            if self.metric_profile is None or self.exclusion_reason is not None:
                _raise_contract_error("measured carrier requires only a metric profile")
        elif self.metric_profile is not None or self.exclusion_reason is None:
            _raise_contract_error("excluded carrier requires only an exclusion reason")
        return self

    def matcher_identity(self) -> tuple[tuple[str, ...], ...]:
        """Return the order-independent matcher identity."""
        return (
            tuple(sorted(self.extensions)),
            tuple(sorted(self.include)),
            tuple(sorted(self.exclude)),
        )


class CarrierManifest(BaseModel):
    """Complete immutable carrier manifest for Budget Contract v2."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_id: Literal["ethos-source-budget-carriers-v2"] = Field(alias="schema")
    contract_version: PositiveInt
    carriers: tuple[CarrierIdentity, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_carriers(self) -> Self:
        """Reject duplicate stable ids and duplicate matcher identities."""
        ids = tuple(item.carrier_id for item in self.carriers)
        if len(ids) != len(set(ids)):
            _raise_contract_error("carrier ids must be unique")
        matchers = tuple(item.matcher_identity() for item in self.carriers)
        if len(matchers) != len(set(matchers)):
            _raise_contract_error("carrier matcher identities must be unique")
        return self


class CarrierMatch(BaseModel):
    """One explicit exact-one carrier classification result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_path: NonEmptyStr
    state: CarrierState
    identity: CarrierIdentity | None
    matched_carrier_ids: tuple[str, ...]
    required_gaps: tuple[str, ...]


class CarrierInventory(BaseModel):
    """Deterministic classification of one repository path inventory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_digest: Sha256
    inventory_digest: Sha256
    matches: tuple[CarrierMatch, ...]
    required_gaps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CarrierManifestLoad:
    """A manifest read that yields typed truth or explicit required gaps."""

    manifest: CarrierManifest | None
    required_gaps: tuple[str, ...]


def validate_carrier_manifest(payload: object) -> CarrierManifest:
    """Validate one carrier manifest payload."""
    return CarrierManifest.model_validate(payload)


def carrier_manifest_json_schema() -> dict[str, object]:
    """Generate the published carrier-manifest JSON Schema."""
    return {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        **CarrierManifest.model_json_schema(by_alias=True),
        "title": "ETHOS Source Budget Carrier Manifest",
    }


def carrier_manifest_digest(manifest: CarrierManifest) -> str:
    """Return the canonical semantic digest for one manifest."""
    payload = manifest.model_dump(mode="json", by_alias=True)
    payload["carriers"] = [
        _canonical_identity(item)
        for item in sorted(manifest.carriers, key=lambda item: item.carrier_id)
    ]
    return _canonical_digest(payload)


def classify_carrier(relative: str, manifest: CarrierManifest) -> CarrierMatch:
    """Classify one repository-relative path without priority semantics."""
    if not _valid_relative_path(relative):
        return _failed_match(
            relative or "<empty>",
            "unclassified",
            (),
            f"source_budget_carrier_path_invalid:{relative or '<empty>'}",
        )
    matched = tuple(
        sorted(
            (item for item in manifest.carriers if _identity_matches(relative, item)),
            key=lambda item: item.carrier_id,
        )
    )
    ids = tuple(item.carrier_id for item in matched)
    if len(matched) == 1:
        identity = matched[0]
        return CarrierMatch(
            relative_path=relative,
            state="classified" if identity.disposition == "measure" else "excluded",
            identity=identity,
            matched_carrier_ids=ids,
            required_gaps=(),
        )
    if len(matched) > 1:
        return _failed_match(
            relative,
            "ambiguous",
            ids,
            f"source_budget_carrier_ambiguous:{relative}:{','.join(ids)}",
        )
    suffix = PurePosixPath(relative).suffix
    registered = {extension for item in manifest.carriers for extension in item.extensions}
    if suffix and suffix not in registered:
        return _failed_match(
            relative,
            "unsupported",
            (),
            f"source_budget_carrier_unsupported:{relative}:{suffix}",
        )
    return _failed_match(
        relative,
        "unclassified",
        (),
        f"source_budget_carrier_unclassified:{relative}",
    )


def classify_carriers(
    paths: Iterable[str],
    manifest: CarrierManifest,
) -> CarrierInventory:
    """Classify a path inventory in stable order and retain every failure."""
    matches = tuple(classify_carrier(path, manifest) for path in sorted(set(paths)))
    manifest_sha256 = carrier_manifest_digest(manifest)
    inventory_payload = {
        "manifest_digest": manifest_sha256,
        "matches": [
            {
                "relative_path": match.relative_path,
                "state": match.state,
                "carrier_id": match.identity.carrier_id if match.identity else None,
                "matched_carrier_ids": list(match.matched_carrier_ids),
                "required_gaps": list(match.required_gaps),
            }
            for match in matches
        ],
    }
    gaps = tuple(dict.fromkeys(gap for match in matches for gap in match.required_gaps))
    return CarrierInventory(
        manifest_digest=manifest_sha256,
        inventory_digest=_canonical_digest(inventory_payload),
        matches=matches,
        required_gaps=gaps,
    )


def _canonical_identity(identity: CarrierIdentity) -> dict[str, object]:
    payload = identity.model_dump(mode="json")
    for field in ("extensions", "include", "exclude"):
        payload[field] = sorted(payload[field])
    return payload


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_relative_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    return bool(
        relative
        and not path.is_absolute()
        and not relative.startswith("./")
        and "\\" not in relative
        and ".." not in path.parts
        and "\x00" not in relative
    )


def _identity_matches(relative: str, identity: CarrierIdentity) -> bool:
    suffix = PurePosixPath(relative).suffix
    if identity.extensions and suffix not in identity.extensions:
        return False
    if not any(fnmatchcase(relative, pattern) for pattern in identity.include):
        return False
    return not any(fnmatchcase(relative, pattern) for pattern in identity.exclude)


def _failed_match(
    relative: str,
    state: Literal["unclassified", "ambiguous", "unsupported"],
    matched_ids: tuple[str, ...],
    gap: str,
) -> CarrierMatch:
    return CarrierMatch(
        relative_path=relative,
        state=state,
        identity=None,
        matched_carrier_ids=matched_ids,
        required_gaps=(gap,),
    )
