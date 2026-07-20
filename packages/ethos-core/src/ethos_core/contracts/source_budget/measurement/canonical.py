"""Domain-separated canonical digests for Budget Contract v2 measurement."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__: tuple[str, ...] = ()

SCHEMA_VERSION = 1


def resolved_model_digest(contracts: tuple[BaseModel, ...]) -> str:
    """Canonicalize typed contracts before hashing."""
    return _digest("resolved_metric_contracts", [_model_payload(item) for item in contracts])


def native_model_digest(
    content_sha256: str,
    normalized_digest: str,
    resolved_digest: str,
    values: tuple[BaseModel, ...],
) -> str:
    """Canonicalize typed metric values before hashing."""
    return _digest(
        "native_measurement",
        {
            "content_sha256": content_sha256,
            "normalized_digest": normalized_digest,
            "resolved_contracts_digest": resolved_digest,
            "values": [_model_payload(item) for item in values],
        },
    )


def carrier_model_digest(
    relative_path: str,
    identity: BaseModel,
    contract_set_digest: str,
    native: BaseModel,
) -> str:
    """Canonicalize typed carrier and native models before hashing."""
    payload = _model_payload(identity)
    for field in ("extensions", "include", "exclude"):
        payload[field] = sorted(cast("list[str]", payload[field]))
    native_payload = _model_payload(native)
    return _digest(
        "carrier_measurement",
        {
            "relative_path": relative_path,
            "identity": payload,
            "contract_set_digest": contract_set_digest,
            "native_measurement_digest": cast("str", native_payload["measurement_digest"]),
        },
    )


def vector_model_digest(coordinates: tuple[BaseModel, ...]) -> str:
    """Canonicalize typed coordinates before hashing."""
    return _digest("measurement_vector", [_model_payload(item) for item in coordinates])


def snapshot_model_digest(
    manifest_digest: str,
    inventory_digest: str,
    contract_set_digest: str,
    measurements: tuple[BaseModel, ...],
    coordinates: tuple[BaseModel, ...],
) -> str:
    """Canonicalize typed snapshot members before hashing."""
    measurement_vector_digest = vector_model_digest(coordinates)
    return _digest(
        "measurement_snapshot",
        {
            "manifest_digest": manifest_digest,
            "inventory_digest": inventory_digest,
            "contract_set_digest": contract_set_digest,
            "measurements": [_measurement_ref(item) for item in measurements],
            "coordinates": [_model_payload(item) for item in coordinates],
            "vector_digest": measurement_vector_digest,
        },
    )


def is_valid_relative_path(relative: str) -> bool:
    """Return whether one string is a canonical repository-relative path."""
    try:
        relative.encode("utf-8")
    except UnicodeEncodeError:
        return False
    if (
        not relative
        or relative.startswith(("/", "./"))
        or chr(92) in relative
        or chr(0) in relative
    ):
        return False
    return all(part not in {"", ".", ".."} for part in relative.split("/"))


def _model_payload(model: BaseModel) -> dict[str, object]:
    return cast("dict[str, object]", model.model_dump(mode="json"))


def _measurement_ref(model: BaseModel) -> dict[str, str]:
    payload = _model_payload(model)
    return {
        "relative_path": cast("str", payload["relative_path"]),
        "measurement_digest": cast("str", payload["measurement_digest"]),
    }


def _digest(kind: str, payload: object) -> str:
    try:
        encoded = json.dumps(
            {"kind": kind, "schema_version": SCHEMA_VERSION, "payload": payload},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except UnicodeEncodeError as error:
        message = "measurement canonical payload must be UTF-8"
        raise ValueError(message) from error
    return hashlib.sha256(encoded).hexdigest()
