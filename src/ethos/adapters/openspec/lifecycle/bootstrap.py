"""Select exact official Change bootstrap artifacts without claiming existing intent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from pathlib import Path


def bootstrap_artifacts(
    root: Path, official: dict[str, object], paths: tuple[str, ...]
) -> tuple[str, tuple[str, ...], str]:
    """Prefer an exact new metadata request over an incomplete neighbor."""
    new = _new_change_metadata_artifact(root, official, paths)
    if new[0]:
        return new
    return _active_bootstrap_artifacts(official) or new


def _listed_change_names(official: dict[str, object]) -> frozenset[str] | None:
    """Read native list identities without treating their presence as an exclusion."""
    commands = official.get("commands")
    listed = commands.get("list") if isinstance(commands, dict) else None
    payload = listed.get("json") if isinstance(listed, dict) else None
    changes = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(changes, list):
        return None
    names: set[str] = set()
    for row in changes:
        name = row.get("name") if isinstance(row, dict) else None
        if not isinstance(name, str) or logical_change_identifier_issue(name) or name in names:
            return None
        names.add(name)
    return frozenset(names)


def _active_bootstrap_artifacts(
    official: dict[str, object],
) -> tuple[str, tuple[str, ...], str] | None:
    lifecycle = official.get("lifecycle")
    changes = lifecycle.get("changes") if isinstance(lifecycle, dict) else None
    if not isinstance(changes, list) or len(changes) != 1 or not isinstance(changes[0], dict):
        return None
    change = str(changes[0].get("name") or "")
    artifacts = changes[0].get("artifacts")
    if logical_change_identifier_issue(change) or not isinstance(artifacts, list) or not artifacts:
        return None
    if f"openspec_status_incomplete:{change}" not in string_sequence(official.get("required_gaps")):
        return None
    change_root = active_change_root(change)
    outputs = [f"{change_root}/.openspec.yaml"]
    ready = ""
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return None
        identifier = str(artifact.get("id") or "")
        output = str(artifact.get("outputPath") or "")
        status = str(artifact.get("status") or "")
        requires = artifact.get("requires")
        if not identifier or not output or not status or not isinstance(requires, list):
            return None
        outputs.append(f"{change_root}/{output}")
        if not ready and status == "ready":
            ready = identifier
    next_action = (
        f"openspec instructions {ready} --change {change} --json"
        if ready
        else f"openspec status --change {change} --json"
    )
    return change, tuple(dict.fromkeys(outputs)), next_action


def _new_change_metadata_artifact(
    root: Path, official: dict[str, object], paths: tuple[str, ...]
) -> tuple[str, tuple[str, ...], str]:
    names = _listed_change_names(official)
    if names is None or len(paths) != 1:
        return "", (), ""
    metadata = paths[0]
    parts = metadata.split("/")
    if len(parts) != 4 or parts[:2] != ["openspec", "changes"] or parts[3] != ".openspec.yaml":
        return "", (), ""
    change = parts[2]
    if change == "archive" or logical_change_identifier_issue(change) or change in names:
        return "", (), ""
    target = root / active_change_root(change)
    if target.exists() or target.is_symlink():
        return "", (), ""
    return change, (metadata,), f"openspec new change {change} --json"


def new_change_root_intent(root: Path, official: dict[str, object], paths: tuple[str, ...]) -> str:
    """Direct an exact absent root to its metadata prewrite, even with peers."""
    names = _listed_change_names(official)
    if names is None or len(paths) != 1:
        return ""
    parts = paths[0].rstrip("/").split("/")
    if len(parts) != 3 or parts[:2] != ["openspec", "changes"]:
        return ""
    change = parts[2]
    target = root / paths[0]
    if (
        change == "archive"
        or logical_change_identifier_issue(change)
        or change in names
        or target.exists()
        or target.is_symlink()
    ):
        return ""
    return change
