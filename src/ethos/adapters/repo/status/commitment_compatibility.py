"""Read-only compatibility projection for one terminal-v1 repository Commitment."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import cast

from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from pathlib import Path

_CARRIER = ".ethos/commitment.toml"
_FIELDS = {
    "schema_version",
    "id",
    "intent",
    "subjects",
    "scope",
    "invariants",
    "acceptance",
    "risks",
    "authority_refs",
    "hypotheses",
    "dependencies",
}
_SEQUENCE_FIELDS = _FIELDS - {"schema_version", "id", "intent"}


def terminal_v1_repository_projection(repo: Path) -> dict[str, object] | None:
    """Read exact terminal-v1 bytes without exposing them as v2 authority."""
    carrier = repo / _CARRIER
    try:
        raw = carrier.read_bytes()
        payload = tomllib.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise _invalid() from error
    if payload.get("schema_version", 1) != 1:
        return None
    if set(payload) - _FIELDS:
        raise _invalid()
    identifier = payload.get("id")
    intent = payload.get("intent")
    subjects = payload.get("subjects")
    if (
        not isinstance(identifier, str)
        or not identifier.startswith("repository:")
        or not isinstance(intent, str)
        or not intent
        or subjects != [identifier]
    ):
        raise _invalid()
    commitment: dict[str, object] = {
        "schema_version": 1,
        "id": identifier,
        "intent": intent,
        "subjects": subjects,
    }
    for field in _SEQUENCE_FIELDS - {"subjects"}:
        values = payload.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise _invalid()
        commitment[field] = values
    scope = cast("list[str]", commitment["scope"])
    if len(scope) != len(set(scope)) or any(not _valid_scope(pattern) for pattern in scope):
        raise _invalid()
    return {
        "commitment": commitment,
        "compatibility": {
            "carrier": _CARRIER,
            "carrier_bytes_sha256": hashlib.sha256(raw).hexdigest(),
            "mode": "terminal_v1_read_only",
            "mutation_authority": False,
            "proof_authority": False,
            "schema_version": 1,
        },
        "legacy_semantic_digest": canonical_json_digest(commitment),
    }


def _valid_scope(pattern: str) -> bool:
    path = PurePosixPath(pattern)
    return bool(
        pattern
        and not pattern.startswith("/")
        and "\\" not in pattern
        and not any(part in {"", ".", ".."} for part in path.parts)
    )


def _invalid() -> ValueError:
    return ValueError(f"repository_commitment_terminal_v1_invalid:{_CARRIER}")
