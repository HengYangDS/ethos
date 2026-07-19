"""Typed carrier contracts for Budget Contract v2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import cache
from itertools import combinations
from itertools import pairwise
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
MIN_AMBIGUOUS_MATCHES = 2
MIN_CANONICAL_ALIAS_SEGMENTS = 2
INVALID_PATH_LABEL_PREFIX = "<invalid-path:"
INVALID_PATH_LABEL_SUFFIX = ">"
INVALID_PATH_DIGEST_LENGTH = 64

CarrierRole = Literal[
    "authored_behavioral_source",
    "authored_declarative_source",
    "test_source",
    "derived_projection",
    "evidence_instance",
    "governance_history",
    "documentation",
    "vendor_or_lock",
    "runtime_local",
]
CarrierDisposition = Literal["measure", "exclude"]
CarrierPathState = Literal["valid", "invalid"]
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
        if any(
            left.endswith(right) or right.endswith(left) for left, right in combinations(values, 2)
        ):
            _raise_contract_error("carrier extensions must not contain redundant suffixes")
        return values

    @field_validator("include", "exclude")
    @classmethod
    def validate_matchers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Require unique repository-relative POSIX matchers."""
        if len(values) != len(set(values)):
            _raise_contract_error("carrier path matchers must be unique")
        for value in values:
            if not _valid_path_matcher(value):
                _raise_contract_error(
                    "carrier path matchers must be repository-relative POSIX paths"
                )
        if _has_redundant_recursive_basename(values):
            _raise_contract_error("carrier path matchers contain a redundant recursive basename")
        return values

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        """Bind measured and excluded identities to disjoint required fields."""
        if self.extensions and any(
            _terminal_segment_has_partial_glob(pattern)
            for pattern in (*self.include, *self.exclude)
        ):
            _raise_contract_error("carrier extensions and terminal suffix globs must not overlap")
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

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=False,
    )

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
    path_state: CarrierPathState = "valid"
    state: CarrierState
    identity: CarrierIdentity | None
    matched_carrier_ids: tuple[str, ...]
    required_gaps: tuple[str, ...]

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """Bind success and failure states to one coherent exact-one result."""
        if self.path_state == "valid":
            if not _valid_relative_path(self.relative_path):
                _raise_contract_error(
                    "carrier classification result requires a canonical relative path"
                )
        elif not _is_invalid_path_label(self.relative_path):
            _raise_contract_error(
                "carrier classification result invalid paths require a synthetic label"
            )
        if self.path_state == "invalid" and self.state != "unclassified":
            _raise_contract_error(
                "carrier classification result invalid paths must be unclassified"
            )
        if any(not carrier_id for carrier_id in self.matched_carrier_ids):
            _raise_contract_error("carrier classification result matched ids must be non-empty")
        if self.matched_carrier_ids != tuple(sorted(set(self.matched_carrier_ids))):
            _raise_contract_error("carrier classification result matched ids must be stable")
        if any(not gap for gap in self.required_gaps):
            _raise_contract_error("carrier classification result required gaps must be non-empty")
        if self.required_gaps != tuple(sorted(set(self.required_gaps))):
            _raise_contract_error("carrier classification result required gaps must be stable")
        if self.state in {"classified", "excluded"}:
            _validate_successful_match(self)
        else:
            _validate_failed_match(self)
        return self


def _validate_successful_match(match: CarrierMatch) -> None:
    expected_disposition = "measure" if match.state == "classified" else "exclude"
    if match.identity is None or match.identity.disposition != expected_disposition:
        _raise_contract_error("carrier classification result state mismatches identity")
    if match.matched_carrier_ids != (match.identity.carrier_id,):
        _raise_contract_error("carrier classification result requires one matched identity")
    if match.required_gaps:
        _raise_contract_error("carrier classification result success forbids required gaps")


def _validate_failed_match(match: CarrierMatch) -> None:
    if match.identity is not None:
        _raise_contract_error("carrier classification result failure forbids identity")
    if not match.required_gaps:
        _raise_contract_error("carrier classification result failure requires required gaps")
    if match.state == "ambiguous" and len(match.matched_carrier_ids) < MIN_AMBIGUOUS_MATCHES:
        _raise_contract_error("carrier classification result ambiguity requires multiple ids")
    if match.state != "ambiguous" and match.matched_carrier_ids:
        _raise_contract_error("carrier classification result failure forbids matched ids")


class CarrierInventory(BaseModel):
    """Deterministic classification of one repository path inventory."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_digest: Sha256
    inventory_digest: Sha256
    matches: tuple[CarrierMatch, ...]
    required_gaps: tuple[str, ...]

    @model_validator(mode="after")
    def validate_invariants(self) -> Self:
        """Require canonical order, exact gaps, and a content-bound digest."""
        match_keys = tuple((match.relative_path, match.path_state) for match in self.matches)
        if match_keys != tuple(sorted(set(match_keys))):
            _raise_contract_error("carrier inventory matches must be unique and stably ordered")
        expected_gaps = _inventory_required_gaps(self.matches)
        if self.required_gaps != expected_gaps:
            _raise_contract_error("carrier inventory required gaps must equal match gaps")
        expected_digest = _canonical_digest(
            _inventory_payload(
                self.manifest_digest,
                self.matches,
                self.required_gaps,
            )
        )
        if self.inventory_digest != expected_digest:
            _raise_contract_error("carrier inventory digest must match canonical content")
        return self


@dataclass(frozen=True, slots=True)
class CarrierManifestLoad:
    """A manifest read that yields typed truth or explicit required gaps."""

    manifest: CarrierManifest | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require exactly one of a validated manifest or non-empty gaps."""
        if self.manifest is not None and not isinstance(self.manifest, CarrierManifest):
            _raise_contract_error("carrier manifest load requires a typed manifest")
        if not isinstance(self.required_gaps, tuple):
            _raise_contract_error("carrier manifest load required gaps must be a tuple")
        if any(not isinstance(gap, str) or not gap for gap in self.required_gaps):
            _raise_contract_error("carrier manifest load required gaps must be non-empty strings")
        if self.required_gaps != tuple(sorted(set(self.required_gaps))):
            _raise_contract_error(
                "carrier manifest load required gaps must be unique and stably ordered"
            )
        if self.manifest is None and not self.required_gaps:
            _raise_contract_error("carrier manifest load requires non-empty required gaps")
        if self.manifest is not None and self.required_gaps:
            _raise_contract_error("carrier manifest load with data forbids required gaps")


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
        safe_relative = _safe_invalid_path_label(relative)
        return _failed_match(
            safe_relative,
            "unclassified",
            (),
            f"source_budget_carrier_path_invalid:{safe_relative}",
            path_state="invalid",
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
    if suffix and not _matches_extension(relative, registered):
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
    classified = tuple(classify_carrier(path, manifest) for path in sorted(set(paths)))
    matches = tuple(sorted(classified, key=lambda match: (match.relative_path, match.path_state)))
    manifest_sha256 = carrier_manifest_digest(manifest)
    gaps = _inventory_required_gaps(matches)
    return CarrierInventory(
        manifest_digest=manifest_sha256,
        inventory_digest=_canonical_digest(_inventory_payload(manifest_sha256, matches, gaps)),
        matches=matches,
        required_gaps=gaps,
    )


def _inventory_required_gaps(
    matches: tuple[CarrierMatch, ...],
) -> tuple[str, ...]:
    gaps = tuple(dict.fromkeys(gap for match in matches for gap in match.required_gaps))
    if not matches:
        return ("source_budget_carrier_inventory_empty",)
    return gaps


def _inventory_payload(
    manifest_digest: str,
    matches: tuple[CarrierMatch, ...],
    required_gaps: tuple[str, ...],
) -> dict[str, object]:
    return {
        "manifest_digest": manifest_digest,
        "matches": [
            {
                "relative_path": match.relative_path,
                "path_state": match.path_state,
                "state": match.state,
                "identity": (_canonical_identity(match.identity) if match.identity else None),
                "matched_carrier_ids": list(match.matched_carrier_ids),
                "required_gaps": list(match.required_gaps),
            }
            for match in matches
        ],
        "required_gaps": list(required_gaps),
    }


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
    try:
        relative.encode("utf-8")
    except UnicodeEncodeError:
        return False
    if not relative or relative.startswith(("/", "./")) or "\\" in relative or "\x00" in relative:
        return False
    return all(part not in {"", ".", ".."} for part in relative.split("/"))


def _valid_path_matcher(pattern: str) -> bool:
    try:
        pattern.encode("utf-8")
    except UnicodeEncodeError:
        return False
    parts = pattern.split("/")
    has_trailing_recursive_alias = len(parts) >= MIN_CANONICAL_ALIAS_SEGMENTS and parts[
        -MIN_CANONICAL_ALIAS_SEGMENTS:
    ] == ["**", "*"]
    return bool(
        pattern
        and not pattern.startswith(("/", "./"))
        and "\\" not in pattern
        and "\x00" not in pattern
        and all(part not in {"", ".", ".."} for part in parts)
        and all(not any(char in part for char in "?[]") for part in parts)
        and all("**" not in part or part == "**" for part in parts)
        and all(part == "**" or part.count("*") <= 1 for part in parts)
        and not has_trailing_recursive_alias
        and not any(left == right == "**" for left, right in pairwise(parts))
        and not any({left, right} == {"*", "**"} for left, right in pairwise(parts))
    )


def _has_redundant_recursive_basename(patterns: tuple[str, ...]) -> bool:
    pattern_set = set(patterns)
    return any(
        "*" not in pattern and f"**/{pattern.rsplit('/', 1)[-1]}" in pattern_set
        for pattern in patterns
    )


def _terminal_segment_has_partial_glob(pattern: str) -> bool:
    terminal = pattern.rsplit("/", 1)[-1]
    return "*" in terminal and terminal not in {"*", "**"}


def _safe_invalid_path_label(relative: str) -> str:
    encoded = relative.encode("utf-8", errors="surrogatepass")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"{INVALID_PATH_LABEL_PREFIX}{digest}{INVALID_PATH_LABEL_SUFFIX}"


def _is_invalid_path_label(relative: str) -> bool:
    if not (
        relative.startswith(INVALID_PATH_LABEL_PREFIX)
        and relative.endswith(INVALID_PATH_LABEL_SUFFIX)
    ):
        return False
    digest = relative[len(INVALID_PATH_LABEL_PREFIX) : -len(INVALID_PATH_LABEL_SUFFIX)]
    return len(digest) == INVALID_PATH_DIGEST_LENGTH and all(
        char in "0123456789abcdef" for char in digest
    )


def _identity_matches(relative: str, identity: CarrierIdentity) -> bool:
    if identity.extensions and not _matches_extension(relative, identity.extensions):
        return False
    if not any(_path_glob_matches(relative, pattern) for pattern in identity.include):
        return False
    return not any(_path_glob_matches(relative, pattern) for pattern in identity.exclude)


def _path_glob_matches(relative: str, pattern: str) -> bool:
    path_parts = tuple(relative.split("/"))
    pattern_parts = tuple(pattern.split("/"))

    @cache
    def matches(path_index: int, pattern_index: int) -> bool:
        if pattern_index == len(pattern_parts):
            return path_index == len(path_parts)
        pattern_part = pattern_parts[pattern_index]
        if pattern_part == "**":
            if pattern_index == len(pattern_parts) - 1:
                return pattern_index == 0 or path_index < len(path_parts)
            return matches(path_index, pattern_index + 1) or (
                path_index < len(path_parts) and matches(path_index + 1, pattern_index)
            )
        return bool(
            path_index < len(path_parts)
            and fnmatchcase(path_parts[path_index], pattern_part)
            and matches(path_index + 1, pattern_index + 1)
        )

    return matches(0, 0)


def _matches_extension(relative: str, extensions: Iterable[str]) -> bool:
    return any(relative.endswith(extension) for extension in extensions)


def _failed_match(
    relative: str,
    state: Literal["unclassified", "ambiguous", "unsupported"],
    matched_ids: tuple[str, ...],
    gap: str,
    *,
    path_state: CarrierPathState = "valid",
) -> CarrierMatch:
    return CarrierMatch(
        relative_path=relative,
        path_state=path_state,
        state=state,
        identity=None,
        matched_carrier_ids=matched_ids,
        required_gaps=(gap,),
    )
