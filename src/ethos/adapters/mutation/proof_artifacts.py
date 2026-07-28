"""Content-addressed storage and validation for proof Attestation artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ethos.contracts.semantic import Attestation

_ARTIFACT_SUBDIR = Path("artifacts")
_HEX = frozenset("0123456789abcdef")
_SHA256_HEX_LENGTH = hashlib.sha256().digest_size * 2


def write_content_addressed(path: Path, payload: bytes, *, collision: str) -> Path:
    """Write immutable payload bytes, rejecting an identity collision."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        try:
            existing = path.read_bytes()
        except OSError as error:
            raise ValueError(collision) from error
        if existing != payload:
            raise ValueError(collision) from None
    return path


def normalize_checks(checks: object, *, allow_empty: bool = False) -> tuple[dict[str, object], ...]:
    """Validate and normalize one ordered collection of gate checks."""
    if not isinstance(checks, list | tuple):
        raise TypeError("proof_attestation_checks_required")
    if not checks:
        if allow_empty:
            return ()
        raise ValueError("proof_attestation_checks_required")
    normalized: list[dict[str, object]] = []
    for raw in checks:
        if not isinstance(raw, Mapping):
            raise TypeError("proof_attestation_check_invalid")
        action_id = raw.get("action_id")
        command = raw.get("command")
        verdict = raw.get("verdict")
        exit_code = raw.get("exit_code")
        message = f"proof_attestation_check_invalid:{action_id}"
        if (
            not isinstance(action_id, str)
            or not action_id
            or not isinstance(command, list | tuple)
            or not command
            or any(not isinstance(token, str) or not token for token in command)
            or not isinstance(verdict, str)
            or verdict not in {"pass", "block", "unknown"}
            or isinstance(exit_code, bool)
            or (exit_code is not None and not isinstance(exit_code, int))
        ):
            raise ValueError(message)
        diagnostics = raw.get("diagnostics", ())
        if not isinstance(diagnostics, list | tuple) or any(
            not isinstance(item, Mapping) or any(not isinstance(name, str) for name in item)
            for item in diagnostics
        ):
            raise TypeError(message)
        normalized.append(
            {
                "action_id": action_id,
                "command": list(command),
                "exit_code": exit_code,
                "stdout": str(raw.get("stdout") or ""),
                "stderr": str(raw.get("stderr") or ""),
                "verdict": verdict,
                "evidence_class": str(raw.get("evidence_class") or ""),
                "trust_bearing": raw.get("trust_bearing") is True,
                "diagnostics": [_diagnostic(item, action_id) for item in diagnostics],
            }
        )
    if len({check["action_id"] for check in normalized}) != len(normalized):
        raise ValueError("proof_attestation_check_duplicate")
    return tuple(normalized)


def _diagnostic(item: object, action_id: object) -> dict[str, object]:
    message = f"proof_attestation_check_invalid:{action_id}"
    if not isinstance(item, Mapping):
        raise TypeError(message)
    diagnostic: dict[str, object] = {}
    for name, value in item.items():
        if not isinstance(name, str):
            raise TypeError(message)
        diagnostic[name] = value
    return diagnostic


def write_proof_artifact(
    store: Path, head: str, checks: tuple[dict[str, Any], ...]
) -> dict[str, object]:
    """Persist the checks artifact identified by its canonical payload digest."""
    payload = json.dumps(
        {"schema_version": 1, "head": head, "checks": list(checks)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    relative = _ARTIFACT_SUBDIR / f"{digest}.json"
    write_content_addressed(
        store / relative,
        payload,
        collision="proof_attestation_artifact_identity_collision",
    )
    return {
        "path": relative.as_posix(),
        "sha256": f"sha256:{digest}",
        "size_bytes": len(payload),
        "media_type": "application/json",
    }


def scan_attestations(store: Path) -> tuple[tuple[Attestation, ...], list[str]]:
    """Load all valid content-addressed Attestations from one local store."""
    if not store.is_dir():
        return (), []
    attestations: list[Attestation] = []
    gaps: list[str] = []
    for path in sorted(item for item in store.iterdir() if item.is_file()):
        if not _is_identity_name(path):
            gaps.append(f"attestation_store_filename_invalid:{path.name}")
            continue
        try:
            attestation = Attestation.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            gaps.append(f"attestation_store_invalid:{path.name}")
            continue
        if attestation.id != path.stem:
            gaps.append(f"attestation_store_identity_mismatch:{path.name}")
            continue
        attestations.append(attestation)
    return tuple(attestations), gaps


def artifact_checks(
    store: Path, attestation: Attestation
) -> tuple[tuple[dict[str, Any], ...] | None, list[str]]:
    """Load checks only when the Attestation binds their immutable artifact."""
    artifact = attestation.statement.get("artifact")
    relative = (_ARTIFACT_SUBDIR / f"{attestation.effect_digest}.json").as_posix()
    if not isinstance(artifact, Mapping):
        return None, ["proof_attestation_artifact_missing"]
    if (
        artifact.get("path") != relative
        or artifact.get("sha256") != f"sha256:{attestation.effect_digest}"
        or attestation.evidence_refs != (f"sha256:{attestation.effect_digest}",)
    ):
        return None, ["proof_attestation_artifact_binding_mismatch"]
    path = store / relative
    try:
        payload = path.read_bytes()
    except OSError:
        return None, [
            "proof_attestation_artifact_missing"
            if not path.is_file()
            else "proof_attestation_artifact_unavailable"
        ]
    if hashlib.sha256(payload).hexdigest() != attestation.effect_digest:
        return None, ["proof_attestation_artifact_digest_mismatch"]
    if artifact.get("size_bytes") != len(payload):
        return None, ["proof_attestation_artifact_size_mismatch"]
    try:
        document = json.loads(payload)
    except json.JSONDecodeError:
        return None, ["proof_attestation_artifact_invalid"]
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("head") != attestation.statement.get("head")
    ):
        return None, ["proof_attestation_artifact_content_mismatch"]
    try:
        return normalize_checks(document.get("checks"), allow_empty=True), []
    except (TypeError, ValueError) as error:
        return None, [str(error)]


def _is_identity_name(path: Path) -> bool:
    return (
        path.suffix == ".json"
        and len(path.stem) == _SHA256_HEX_LENGTH
        and not (set(path.stem) - _HEX)
    )
