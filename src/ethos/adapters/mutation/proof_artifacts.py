"""Content-addressed storage and validation for proof Attestation artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.semantic import Attestation
from ethos.repository.policy.gates import canonical_gate_command

_ARTIFACT_SUBDIR = Path("artifacts")
_HEX = frozenset("0123456789abcdef")
_SHA256_HEX_LENGTH = hashlib.sha256().digest_size * 2
_ARTIFACT_CONTENT_MISMATCH = "proof_attestation_artifact_content_mismatch"
_ARTIFACT_INVALID = "proof_attestation_artifact_invalid"
_CHECK_INVALID = "proof_attestation_check_invalid"
_CHECKS_REQUIRED = "proof_attestation_checks_required"
_DEFAULT_ATTESTATION_DIR = Path(".ethos") / "state" / "attestations"
_TEST_ATTESTATION_STATE_DIR_ENV = "ETHOS_TEST_ATTESTATION_STATE_DIR"


def attestation_store_dir(root: Path) -> Path:
    """Return the one ignored content-addressed local Attestation store."""
    override = os.environ.get(_TEST_ATTESTATION_STATE_DIR_ENV, "").strip()
    pytest_active = os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_XDIST_WORKER")
    if override and pytest_active:
        path = Path(override).expanduser()
        if path.is_absolute():
            return path
        common = git_common_dir(root)
        return (Path(common) if common else root) / path
    common = git_common_dir(root)
    return local_state_root(root) / "attestations" if common else root / _DEFAULT_ATTESTATION_DIR


def persist_attestation(root: Path, attestation: Attestation) -> Path:
    """Persist one validated Attestation in the sole local Attestation store."""
    payload = attestation.canonical_json().encode("utf-8")
    Attestation.model_validate_json(payload)
    return write_content_addressed(
        attestation_store_dir(root) / f"{attestation.id}.json",
        payload,
        collision="attestation_identity_collision",
    )


def _decode_artifact(payload: bytes, head: object) -> tuple[dict[str, Any], ...]:
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError(_ARTIFACT_INVALID) from error
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("head") != head
    ):
        raise ValueError(_ARTIFACT_CONTENT_MISMATCH)
    return normalize_checks(document.get("checks"), allow_empty=True)


def normalize_checks(checks: object, *, allow_empty: bool = False) -> tuple[dict[str, object], ...]:
    """Validate and normalize one ordered collection of gate checks."""
    if not isinstance(checks, list | tuple):
        raise TypeError(_CHECKS_REQUIRED)
    if not checks:
        if allow_empty:
            return ()
        raise ValueError(_CHECKS_REQUIRED)
    normalized: list[dict[str, object]] = []
    for raw in checks:
        if not isinstance(raw, Mapping):
            raise TypeError(_CHECK_INVALID)
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
        normalized_diagnostics = [dict(item) for item in diagnostics if isinstance(item, Mapping)]
        normalized.append(
            {
                "action_id": action_id,
                "command": list(canonical_gate_command(tuple(str(token) for token in command))),
                "exit_code": exit_code,
                "stdout": str(raw.get("stdout") or ""),
                "stderr": str(raw.get("stderr") or ""),
                "verdict": verdict,
                "evidence_class": str(raw.get("evidence_class") or ""),
                "trust_bearing": raw.get("trust_bearing") is True,
                "diagnostics": normalized_diagnostics,
            }
        )
    if len({check["action_id"] for check in normalized}) != len(normalized):
        message = "proof_attestation_check_duplicate"
        raise ValueError(message)
    return tuple(normalized)


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
    gap = ""
    payload = b""
    if not isinstance(artifact, Mapping):
        gap = "proof_attestation_artifact_missing"
    else:
        digest = str(artifact.get("sha256") or "").removeprefix("sha256:")
        relative = (_ARTIFACT_SUBDIR / f"{digest}.json").as_posix()
        if (
            set(artifact) != {"path", "sha256", "size_bytes", "media_type"}
            or len(digest) != _SHA256_HEX_LENGTH
            or set(digest) - _HEX
            or artifact.get("path") != relative
            or artifact.get("sha256") != f"sha256:{digest}"
            or artifact.get("media_type") != "application/json"
            or attestation.evidence_refs != (f"sha256:{digest}",)
        ):
            return None, ["proof_attestation_artifact_binding_mismatch"]
        path = store / relative
        try:
            payload = path.read_bytes()
        except OSError:
            gap = (
                "proof_attestation_artifact_missing"
                if not path.is_file()
                else "proof_attestation_artifact_unavailable"
            )
    if not gap and hashlib.sha256(payload).hexdigest() != digest:
        gap = "proof_attestation_artifact_digest_mismatch"
    if not gap and artifact.get("size_bytes") != len(payload):
        gap = "proof_attestation_artifact_size_mismatch"
    if gap:
        return None, [gap]
    try:
        plan = attestation.statement.get("plan")
        facts = plan.get("facts") if isinstance(plan, Mapping) else None
        head = facts.get("head") if isinstance(facts, Mapping) else None
        checks = _decode_artifact(payload, head)
    except (TypeError, ValueError) as error:
        return None, [str(error)]
    return checks, []


def _is_identity_name(path: Path) -> bool:
    return (
        path.suffix == ".json"
        and len(path.stem) == _SHA256_HEX_LENGTH
        and not (set(path.stem) - _HEX)
    )
