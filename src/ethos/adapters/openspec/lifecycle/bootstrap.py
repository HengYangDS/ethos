"""Select exact official Change bootstrap artifacts without claiming existing intent."""

from __future__ import annotations

from pathlib import Path

from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue


def bootstrap_artifacts(
    root: Path, official: dict[str, object], paths: tuple[str, ...]
) -> tuple[str, tuple[str, ...], str]:
    """Prefer an exact new metadata request over an incomplete neighbor."""
    new = _new_change_metadata_artifact(root, official, paths)
    if new[0]:
        return new
    return _active_bootstrap_artifacts(root, official, paths) or new


def _listed_change_names(official: dict[str, object]) -> frozenset[str] | None:
    """Read native list identities without treating their presence as an exclusion.

    A legacy peer may keep its dated name: that breaks only the naming rule a new target
    must meet. A malformed or repeated name is no safe identity, so nothing is selected.
    """
    commands = official.get("commands")
    listed = commands.get("list") if isinstance(commands, dict) else None
    payload = listed.get("json") if isinstance(listed, dict) else None
    changes = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(changes, list):
        return None
    names: set[str] = set()
    for row in changes:
        name = row.get("name") if isinstance(row, dict) else None
        if (
            not isinstance(name, str)
            or logical_change_identifier_issue(name) not in {"", "temporal_suffix"}
            or name in names
        ):
            return None
        names.add(name)
    return frozenset(names)


def _active_bootstrap_artifacts(
    root: Path, official: dict[str, object], paths: tuple[str, ...]
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
        return _tracked_task_repair(root, official, change, paths)
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


def _tracked_task_repair(
    root: Path, official: dict[str, object], change: str, paths: tuple[str, ...]
) -> tuple[str, tuple[str, ...], str] | None:
    """Repair only the selected native tracking artifact, not unrelated product work."""
    commands = string_mapping(official.get("commands"))
    status_result, apply_result = (string_mapping(commands.get(key)) for key in ("status", "apply"))
    if string_sequence(official.get("required_gaps")) != [
        f"openspec_apply_blocked:{change}"
    ] or any(
        result.get("exit_code") != 0 or result.get("parse_error")
        for result in (status_result, apply_result)
    ):
        return None
    status, apply, binding = (
        string_mapping(value)
        for value in (
            status_result.get("json"),
            apply_result.get("json"),
            status_result.get("task_tracking"),
        )
    )
    directory = root.resolve() / active_change_root(change)
    schema, identifier = status.get("schemaName"), binding.get("artifactId")
    outputs = object_sequence(binding.get("outputPaths"))
    selected = [
        string_mapping(row)
        for row in object_sequence(status.get("artifacts"))
        if string_mapping(row).get("id") == identifier
    ]
    projected = string_mapping(string_mapping(status.get("artifactPaths")).get(identifier))
    if (
        not isinstance(schema, str)
        or not schema
        or not isinstance(identifier, str)
        or not identifier
        or any(
            value.get("changeName") != change or value.get("schemaName") != schema
            for value in (apply, binding)
        )
        or any(value.get("changeRoot") != str(directory) for value in (status, binding))
        or apply.get("changeDir") != str(directory)
        or status.get("isComplete") is not True
        or binding.get("configured") is not True
        or apply.get("taskTrackingConfigured") is not True
        or apply.get("state") != "blocked"
        or any(
            apply.get(key)
            for key in ("missingArtifacts", "missingPrerequisites", "unavailableTrackingFiles")
        )
        or len(selected) != 1
        or selected[0].get("status") != "done"
        or not outputs
        or any(not isinstance(value, str) or not value for value in outputs)
        or projected.get("outputPath") != selected[0].get("outputPath")
        or projected.get("existingOutputPaths") != outputs
        or string_mapping(apply.get("contextFiles")).get(identifier) != outputs
    ):
        return None
    try:
        files = tuple(Path(value) for value in outputs if isinstance(value, str))
        if any(
            path.resolve() != path or not path.is_file() or not path.is_relative_to(directory)
            for path in files
        ):
            return None
        bound = tuple(path.relative_to(root.resolve()).as_posix() for path in files)
    except (OSError, RuntimeError, ValueError):
        return None
    return (
        change,
        bound if all(path in bound for path in paths) else (),
        f"openspec instructions {identifier} --change {change} --json",
    )


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
