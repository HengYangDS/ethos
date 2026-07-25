"""Private shared helpers for lane-resolution adapters."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.resolution.records.io.posix as record_posix

if TYPE_CHECKING:
    from collections.abc import Mapping

LEGACY_ARTIFACT_ROOT = Path("build/artifacts/lane-resolution")
_MAX_CHRONICLE_BYTES = 1024 * 1024
_MIN_CHRONICLE_REF_PARTS = 3
_DISPOSITION_STATES = {
    "block": "blocked_by_decision",
    "preserve": "preserved",
    "retire": "retired",
    "preserve-retire": "preserved_and_retired",
}


def record_destination_safe(record_root: Path, destination: Path) -> bool:
    """Return whether a record path stays under non-symlinked owner components."""
    lexical_root = record_root.absolute()
    lexical_destination = destination.absolute()
    try:
        relative_destination = lexical_destination.relative_to(lexical_root)
    except ValueError:
        return False
    if ".." in relative_destination.parts:
        return False
    try:
        resolved_root = lexical_root.resolve()
    except (OSError, RuntimeError):
        return False
    if resolved_root != lexical_root:
        return False
    current = lexical_root
    for part in relative_destination.parts:
        current /= part
        if current.is_symlink():
            return False
    try:
        destination_safe = lexical_destination.resolve().is_relative_to(resolved_root)
    except (OSError, RuntimeError):
        destination_safe = False
    return destination_safe


def valid_decision_id(value: str) -> bool:
    """Return whether the identifier is exactly lane-decision:<canonical UUID>."""
    prefix = "lane-decision:"
    if not value.startswith(prefix):
        return False
    try:
        parsed = uuid.UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return value == f"{prefix}{parsed}"


def transition_gap(error: Exception, fallback: str) -> str:
    """Preserve one stable resolution gap and otherwise use the bounded fallback."""
    message = str(error).strip()
    return message if message.startswith(("lane_resolution_", "lane_closeout_")) else fallback


def canonical_package_path(artifact_root: Path, decision_id: str) -> Path | None:
    """Resolve a package destination without allowing traversal or symlink escape."""
    if not valid_decision_id(decision_id):
        return None
    candidate = artifact_root / decision_id
    return candidate if record_destination_safe(artifact_root, candidate) else None


def display_path(root: Path, path: Path) -> str:
    """Keep legacy paths relative while representing sibling records absolutely."""
    candidate = path.resolve()
    try:
        return candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def sha256_digest(path: Path) -> str:
    """Return the hex sha256 digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_chronicle_matches(root: Path, decision: Mapping[str, object]) -> bool:
    """Match current Chronicle bytes using the admitted lane-resolution semantics."""
    reference = Path(str(decision.get("chronicle_ref") or ""))
    if reference.is_absolute() or ".." in reference.parts:
        return False
    candidate = (root / reference).absolute()
    try:
        relative = candidate.relative_to(root.absolute())
        if (
            relative.parts[:2] != ("evidence", "chronicle")
            or len(relative.parts) < _MIN_CHRONICLE_REF_PARTS
        ):
            return False
        parent = record_posix.open_directory_path(candidate.parent, create=False)
    except (OSError, ValueError):
        return False
    try:
        parent_identity = record_posix.directory_identity(os.fstat(parent))
        identity = record_posix.entry_file_identity(parent, candidate.name)
        content = (
            None
            if identity is None
            else record_posix.read_bound_file(
                parent,
                candidate.name,
                identity,
                max_bytes=_MAX_CHRONICLE_BYTES,
            )
        )
        if content is None or not record_posix.directory_descriptor_is_live(
            candidate.parent, parent, parent_identity
        ):
            return False
        text = content.decode()
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    finally:
        os.close(parent)
    return f"lane_resolution/{decision.get('disposition')}" in text and hashlib.sha256(
        content
    ).hexdigest() == decision.get("chronicle_digest")


def preservation_payloads_match(
    manifest: Mapping[str, object],
    payload_sha256: Mapping[str, str | None],
    present_names: set[str],
) -> bool:
    """Return whether captured package payloads match one preservation manifest."""
    package_format = manifest.get("package_format_version")
    if package_format not in (None, "v2"):
        return False
    required = [
        ("repository.bundle", "bundle_sha256"),
        ("tracked.patch", "patch_sha256"),
    ]
    expected_names = {"manifest.json", "repository.bundle", "tracked.patch"}
    if package_format == "v2":
        required.append(("index.patch", "index_patch_sha256"))
        expected_names.add("index.patch")
    archive_digest = str(manifest.get("untracked_archive_sha256") or "")
    if archive_digest:
        expected_names.add("untracked.tar")
    if present_names != expected_names or any(
        payload_sha256.get(name) != str(manifest.get(field) or "") for name, field in required
    ):
        return False
    return not archive_digest or payload_sha256.get("untracked.tar") == archive_digest


def cross_record_invalid_paths(
    *,
    decisions: dict[str, dict[str, object]],
    manifests: dict[str, dict[str, object]],
    receipts: dict[str, dict[str, object]],
    clears: dict[str, dict[str, object]],
    reservations: dict[str, dict[str, object]],
) -> list[Path]:
    """Return physical records whose bindings disagree within one held snapshot."""
    return [
        *_decision_binding_invalid_paths(
            decisions=decisions,
            manifests=manifests,
            receipts=receipts,
            reservations=reservations,
        ),
        *_artifact_binding_invalid_paths(
            manifests=manifests,
            receipts=receipts,
            clears=clears,
        ),
    ]


def _decision_binding_invalid_paths(
    *,
    decisions: dict[str, dict[str, object]],
    manifests: dict[str, dict[str, object]],
    receipts: dict[str, dict[str, object]],
    reservations: dict[str, dict[str, object]],
) -> list[Path]:
    invalid: list[Path] = []
    for decision_id, decision in decisions.items():
        observation = decision.get("observation")
        expected = (
            cast("Mapping[str, object]", observation) if isinstance(observation, dict) else {}
        )
        manifest = manifests.get(decision_id)
        receipt = receipts.get(decision_id)
        reservation = reservations.get(decision_id)
        if manifest and not _same_binding(manifest, expected, decision):
            invalid.append(cast("Path", manifest["physical_path"]))
        if receipt and not _same_binding(receipt, expected, decision, receipt=True):
            invalid.append(cast("Path", receipt["physical_path"]))
        if reservation and not _reservation_binding(reservation, expected, decision):
            invalid.append(cast("Path", reservation["physical_path"]))
    return invalid


def _artifact_binding_invalid_paths(
    *,
    manifests: dict[str, dict[str, object]],
    receipts: dict[str, dict[str, object]],
    clears: dict[str, dict[str, object]],
) -> list[Path]:
    invalid: list[Path] = []
    for decision_id, receipt in receipts.items():
        preserved = str(receipt.get("state") or "") in {"preserved", "preserved_and_retired"}
        manifest = manifests.get(decision_id)
        clear = clears.get(decision_id)
        if preserved and manifest is None and clear is None:
            invalid.append(cast("Path", receipt["physical_path"]))
        if manifest and receipt.get("preservation_manifest_sha256") != manifest.get(
            "manifest_sha256"
        ):
            invalid.append(cast("Path", receipt["physical_path"]))
        if clear and clear.get("manifest_sha256") != receipt.get("preservation_manifest_sha256"):
            invalid.append(cast("Path", clear["physical_path"]))
    for decision_id, manifest in manifests.items():
        if decision_id not in receipts:
            invalid.append(cast("Path", manifest["physical_path"]))
        if manifest.get("quarantined") is True and decision_id not in clears:
            invalid.append(cast("Path", manifest["physical_path"]))
    for decision_id, clear in clears.items():
        if decision_id not in receipts:
            invalid.append(cast("Path", clear["physical_path"]))
    return invalid


def _same_binding(
    record: Mapping[str, object],
    observation: Mapping[str, object],
    decision: Mapping[str, object],
    *,
    receipt: bool = False,
) -> bool:
    common = (
        record.get("lane_ref") == observation.get("lane_ref")
        and record.get("head") == observation.get("head")
        and record.get("observation_digest") == decision.get("observation_digest")
    )
    if not receipt:
        return common
    binding = record.get("ownerless_closeout_binding")
    ownerless_binding_valid = not _ownerless_retire_candidate(decision, observation) or (
        isinstance(binding, dict)
        and binding.get("decision_sha256") == decision.get("content_sha256")
    )
    return (
        common
        and record.get("state") == _DISPOSITION_STATES.get(str(decision.get("disposition") or ""))
        and record.get("reconciliation_required") is bool(decision.get("break_glass"))
        and ownerless_binding_valid
    )


def _ownerless_retire_candidate(
    decision: Mapping[str, object], observation: Mapping[str, object]
) -> bool:
    return (
        decision.get("disposition") == "retire"
        and observation.get("dirty") is False
        and observation.get("orphan") is True
        and not observation.get("holder_ref")
    )


def _reservation_binding(
    record: Mapping[str, object],
    observation: Mapping[str, object],
    decision: Mapping[str, object],
) -> bool:
    return (
        record.get("lane_ref") == observation.get("lane_ref")
        and record.get("head") == observation.get("head")
        and record.get("decision_sha256") == decision.get("content_sha256")
    )
