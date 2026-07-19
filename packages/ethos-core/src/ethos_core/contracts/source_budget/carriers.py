"""Typed carrier contracts for Budget Contract v2."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import typing as t
from dataclasses import dataclass
from functools import cache
from itertools import combinations
from itertools import pairwise
from typing import TYPE_CHECKING

import pydantic as p

if TYPE_CHECKING:
    from collections.abc import Iterable
NonEmptyStr = t.Annotated[str, p.Field(min_length=1)]
PositiveInt = t.Annotated[int, p.Field(strict=True, gt=0)]
Sha256 = t.Annotated[str, p.Field(pattern="^[a-f0-9]{64}$")]
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
MIN_AMBIGUOUS_MATCHES = 2
CarrierRole = t.Literal[
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
CarrierDisposition = t.Literal["measure", "exclude"]
CarrierPathState = t.Literal["valid", "invalid"]
CarrierState = t.Literal["classified", "excluded", "unclassified", "ambiguous", "unsupported"]


_C = "carrier classification result "
_L = "carrier manifest load "
_I = "carrier inventory "
_X = "carrier extensions "
_P = "carrier path matchers "
_MATCHER_SEGMENT = re.compile(r"(?:\*\*|[^*?\[\]]*\*?[^*?\[\]]*)").fullmatch
_INVALID_LABEL = re.compile("<invalid-path:[a-f0-9]{64}>").fullmatch


def _err(message: str) -> t.NoReturn:
    """Raise one stable carrier-contract validation error."""
    raise ValueError(message)


def _stable(values: tuple[t.Any, ...]) -> bool:
    return values == tuple(sorted(set(values)))


def _unique(values: tuple[t.Any, ...]) -> bool:
    return len(values) == len(set(values))


def _valid_extension(v: str) -> bool:
    return v.startswith(".") and v == v.lower() and "/" not in v and "\\" not in v and len(v) > 1


def _redundant_extension(v: tuple[str, ...]) -> bool:
    return any(a.endswith(b) or b.endswith(a) for a, b in combinations(v, 2))


def _load_envelope(
    v: object, kind: type, gaps: tuple[object, ...], prefix: str, typed: str
) -> None:
    (v is None or isinstance(v, kind)) or _err(prefix + typed)
    isinstance(gaps, tuple) or _err(prefix + "required gaps must be a tuple")
    all(isinstance(gap, str) and gap for gap in gaps) or _err(
        prefix + "required gaps must be non-empty strings"
    )
    _stable(gaps) or _err(prefix + "required gaps must be unique and stably ordered")
    (v is not None or gaps) or _err(prefix + "requires non-empty required gaps")
    (v is None or not gaps) or _err(prefix + "with data forbids required gaps")


def _json_schema(model: type[p.BaseModel], title: str) -> dict[str, object]:
    return {
        "$schema": JSON_SCHEMA_DRAFT_2020_12,
        **model.model_json_schema(by_alias=True),
        "title": title,
    }


class _Frozen(p.BaseModel):
    model_config = p.ConfigDict(frozen=True, extra="forbid")


err, unique, FrozenContract = _err, _unique, _Frozen


class _Registry(_Frozen):
    model_config = p.ConfigDict(validate_by_alias=True, validate_by_name=False)


class CarrierIdentity(_Frozen):
    """One immutable path classifier and its Budget Contract v2 identity."""

    carrier_id: NonEmptyStr
    role: CarrierRole
    scope_id: NonEmptyStr
    disposition: CarrierDisposition
    metric_profile: NonEmptyStr | None = None
    extensions: tuple[str, ...] = ()
    include: tuple[NonEmptyStr, ...] = p.Field(min_length=1)
    exclude: tuple[NonEmptyStr, ...] = ()
    owner: NonEmptyStr
    exclusion_reason: NonEmptyStr | None = None

    @p.field_validator("extensions")
    @classmethod
    def validate_extensions(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Require unique lowercase dotted extensions."""
        _unique(values) or _err(_X + "must be unique")
        all(map(_valid_extension, values)) or _err(_X + "must be lowercase dotted suffixes")
        not _redundant_extension(values) or _err(_X + "must not contain redundant suffixes")
        return values

    @p.field_validator("include", "exclude")
    @classmethod
    def validate_matchers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Require unique repository-relative POSIX matchers."""
        _unique(values) or _err(_P + "must be unique")
        all(map(_valid_matcher, values)) or _err(_P + "must be repository-relative POSIX paths")
        not _redundant(values) or _err(_P + "contain a redundant recursive basename")
        return values

    def model_post_init(self, _context: t.Any) -> None:
        """Bind measured and excluded identities to disjoint required fields."""
        overlap = self.extensions and any(map(_partial_glob, (*self.include, *self.exclude)))
        not overlap or _err(_X + "and terminal suffix globs must not overlap")
        fields = self.metric_profile is not None, self.exclusion_reason is not None
        expected = (True, False) if self.disposition == "measure" else (False, True)
        kind = "metric profile" if expected[0] else "exclusion reason"
        fields == expected or _err(f"{self.disposition}d carrier requires only a {kind}")

    def matcher_identity(self) -> tuple[tuple[str, ...], ...]:
        """Return the order-independent matcher identity."""
        return tuple(
            tuple(sorted(values)) for values in (self.extensions, self.include, self.exclude)
        )


class CarrierManifest(_Registry):
    """Complete immutable carrier manifest for Budget Contract v2."""

    schema_id: t.Literal["ethos-source-budget-carriers-v2"] = p.Field(alias="schema")
    contract_version: PositiveInt
    carriers: tuple[CarrierIdentity, ...] = p.Field(min_length=1)

    def model_post_init(self, _context: t.Any) -> None:
        """Reject duplicate stable ids and duplicate matcher identities."""
        ids = tuple(item.carrier_id for item in self.carriers)
        _unique(ids) or _err("carrier ids must be unique")
        matchers = tuple(item.matcher_identity() for item in self.carriers)
        _unique(matchers) or _err("carrier matcher identities must be unique")


class CarrierMatch(_Frozen):
    """One explicit exact-one carrier classification result."""

    relative_path: NonEmptyStr
    path_state: CarrierPathState = "valid"
    state: CarrierState
    identity: CarrierIdentity | None
    matched_carrier_ids: tuple[str, ...]
    required_gaps: tuple[str, ...]

    def model_post_init(self, _context: t.Any) -> None:
        """Bind success and failure states to one coherent exact-one result."""
        state, ids, gaps = self.state, self.matched_carrier_ids, self.required_gaps
        checker, message = (
            (_valid_path, "requires a canonical relative path")
            if self.path_state == "valid"
            else (_is_invalid_label, "invalid paths require a synthetic label")
        )
        checker(self.relative_path) or _err(_C + message)
        (self.path_state != "invalid" or state == "unclassified") or _err(
            _C + "invalid paths must be unclassified"
        )
        all(ids) or _err(_C + "matched ids must be non-empty")
        _stable(ids) or _err(_C + "matched ids must be stable")
        all(gaps) or _err(_C + "required gaps must be non-empty")
        _stable(gaps) or _err(_C + "required gaps must be stable")
        if state in {"classified", "excluded"}:
            disposition = "measure" if state == "classified" else "exclude"
            identity = self.identity
            if identity is None or identity.disposition != disposition:
                _err(_C + "state mismatches identity")
            ids == (identity.carrier_id,) or _err(_C + "requires one matched identity")
            not gaps or _err(_C + "success forbids required gaps")
        else:
            self.identity is None or _err(_C + "failure forbids identity")
            gaps or _err(_C + "failure requires required gaps")
            (state != "ambiguous" or len(ids) >= MIN_AMBIGUOUS_MATCHES) or _err(
                _C + "ambiguity requires multiple ids"
            )
            (state == "ambiguous" or not ids) or _err(_C + "failure forbids matched ids")


class CarrierInventory(_Frozen):
    """Deterministic classification of one repository path inventory."""

    manifest_digest: Sha256
    inventory_digest: Sha256
    matches: tuple[CarrierMatch, ...]
    required_gaps: tuple[str, ...]

    def model_post_init(self, _context: t.Any) -> None:
        """Require canonical order, exact gaps, and a content-bound digest."""
        match_keys = tuple((match.relative_path, match.path_state) for match in self.matches)
        _stable(match_keys) or _err(_I + "matches must be unique and stably ordered")
        expected_gaps = _gaps(self.matches)
        self.required_gaps == expected_gaps or _err(_I + "required gaps must equal match gaps")
        expected_digest = _digest(_payload(self.manifest_digest, self.matches, self.required_gaps))
        self.inventory_digest == expected_digest or _err(_I + "digest must match canonical content")


@dataclass(frozen=True, slots=True)
class CarrierManifestLoad:
    """A manifest read that yields typed truth or explicit required gaps."""

    manifest: CarrierManifest | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require exactly one of a validated manifest or non-empty gaps."""
        _load_envelope(
            self.manifest,
            CarrierManifest,
            self.required_gaps,
            _L,
            "requires a typed manifest",
        )


def validate_carrier_manifest(payload: object) -> CarrierManifest:
    """Validate one carrier manifest payload."""
    return CarrierManifest.model_validate(payload)


def carrier_manifest_json_schema() -> dict[str, object]:
    """Generate the published carrier-manifest JSON Schema."""
    return _json_schema(CarrierManifest, "ETHOS Source Budget Carrier Manifest")


def carrier_manifest_digest(manifest: CarrierManifest) -> str:
    """Return the canonical semantic digest for one manifest."""
    payload = manifest.model_dump(mode="json", by_alias=True)
    payload["carriers"] = [
        _identity(item) for item in sorted(manifest.carriers, key=lambda item: item.carrier_id)
    ]
    return _digest(payload)


def classify_carrier(relative: str, manifest: CarrierManifest) -> CarrierMatch:
    """Classify one repository-relative path without priority semantics."""
    if not _valid_path(relative):
        safe_relative = _invalid_label(relative)
        return _make_match(
            safe_relative,
            "invalid",
            "unclassified",
            None,
            (),
            (f"source_budget_carrier_path_invalid:{safe_relative}",),
        )
    matched = sorted(
        (item for item in manifest.carriers if _matches(relative, item)),
        key=lambda item: item.carrier_id,
    )
    ids = tuple(item.carrier_id for item in matched)
    if len(matched) == 1:
        identity = matched[0]
        state = "classified" if identity.disposition == "measure" else "excluded"
        return _make_match(relative, "valid", state, identity, ids, ())
    if len(matched) > 1:
        gap = f"source_budget_carrier_ambiguous:{relative}:{','.join(ids)}"
        return _make_match(relative, "valid", "ambiguous", None, ids, (gap,))
    suffix = posixpath.splitext(relative)[1]
    registered = {extension for item in manifest.carriers for extension in item.extensions}
    unsupported = bool(suffix and not any(relative.endswith(ext) for ext in registered))
    state: CarrierState = "unsupported" if unsupported else "unclassified"
    gap = f"source_budget_carrier_{state}:{relative}{f':{suffix}' if unsupported else ''}"
    return _make_match(relative, "valid", state, None, (), (gap,))


def classify_carriers(paths: Iterable[str], manifest: CarrierManifest) -> CarrierInventory:
    """Classify a path inventory in stable order and retain every failure."""
    classified = tuple(classify_carrier(path, manifest) for path in sorted(set(paths)))
    matches = tuple(sorted(classified, key=lambda match: (match.relative_path, match.path_state)))
    manifest_sha256 = carrier_manifest_digest(manifest)
    gaps = _gaps(matches)
    return CarrierInventory(
        manifest_digest=manifest_sha256,
        inventory_digest=_digest(_payload(manifest_sha256, matches, gaps)),
        matches=matches,
        required_gaps=gaps,
    )


def _gaps(matches: tuple[CarrierMatch, ...]) -> tuple[str, ...]:
    return (
        tuple(dict.fromkeys(gap for match in matches for gap in match.required_gaps))
        if matches
        else ("source_budget_carrier_inventory_empty",)
    )


def _payload(
    manifest_digest: str,
    matches: tuple[CarrierMatch, ...],
    required_gaps: tuple[str, ...],
) -> dict[str, object]:
    return {
        "manifest_digest": manifest_digest,
        "matches": [_match_payload(match) for match in matches],
        "required_gaps": list(required_gaps),
    }


def _match_payload(match: CarrierMatch) -> dict[str, object]:
    payload = match.model_dump(mode="json")
    payload["identity"] = _identity(match.identity) if match.identity else None
    return payload


def _identity(identity: CarrierIdentity) -> dict[str, object]:
    payload = identity.model_dump(mode="json")
    for field in ("extensions", "include", "exclude"):
        payload[field] = sorted(payload[field])
    return payload


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _valid_path(value: str) -> bool:
    try:
        return bool(
            value != "."
            and value == posixpath.normpath(value)
            and not value.startswith("/")
            and ".." not in value.split("/")
            and "\\" not in value
            and "\x00" not in value
            and value.encode("utf-8")
        )
    except UnicodeEncodeError:
        return False


def _valid_matcher(pat: str) -> bool:
    parts = pat.split("/")
    return bool(
        _valid_path(pat)
        and all(map(_MATCHER_SEGMENT, parts))
        and all(not (a == b == "**" or {a, b} == {"*", "**"}) for a, b in pairwise(parts))
    )


def _redundant(v: tuple[str, ...]) -> bool:
    patterns = set(v)
    return any("*" not in p and f"**/{p.rsplit('/', 1)[-1]}" in patterns for p in v)


def _partial_glob(pat: str) -> bool:
    terminal = pat.rsplit("/", 1)[-1]
    return "*" in terminal and terminal not in {"*", "**"}


def _invalid_label(r: str) -> str:
    digest = hashlib.sha256(r.encode("utf-8", errors="surrogatepass")).hexdigest()
    return f"<invalid-path:{digest}>"


def _is_invalid_label(r: str) -> bool:
    return _INVALID_LABEL(r) is not None


def _matches(r: str, identity: CarrierIdentity) -> bool:
    return (
        (not identity.extensions or any(r.endswith(ext) for ext in identity.extensions))
        and any(_glob(p).fullmatch(r) for p in identity.include)
        and not any(_glob(p).fullmatch(r) for p in identity.exclude)
    )


@cache
def _glob(pattern: str) -> re.Pattern[str]:
    expression = re.escape(pattern)
    if pattern == "**":
        expression = ".+"
    else:
        expression = expression.replace(r"\*\*/", r"(?:[^/]+/)*")
        expression = expression.replace(r"/\*\*", r"/[^/]+(?:/[^/]+)*")
        expression = expression.replace(r"\*", r"[^/]*")
    return re.compile(expression)


def _make_match(*values: object) -> CarrierMatch:
    return CarrierMatch.model_validate(dict(zip(CarrierMatch.model_fields, values, strict=True)))
