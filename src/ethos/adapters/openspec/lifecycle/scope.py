"""Attribute material changed paths to the selected official OpenSpec Change."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


def material_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] = (),
) -> dict[str, object]:
    """Attribute material paths when exactly one official Change owns the work."""
    paths, patterns, material, applicable = _scope_inputs(root, changed_paths)
    if not applicable:
        return _scope_report(paths, patterns, material, state="not_applicable")
    names = tuple(dict.fromkeys(active_change_names))
    if not material:
        return _scope_report(paths, patterns, material, state="no_material_paths")
    if len(names) != 1:
        gaps = (
            ["openspec_active_change_missing"]
            if not names
            else [f"openspec_active_change_ambiguous:{','.join(names)}"]
        )
        return _scope_report(paths, patterns, material, state="unattributed", gaps=gaps)
    change = names[0]
    owner = {"name": change, "path": f"openspec/changes/{change}"}
    covered: list[dict[str, object]] = [{"path": path, "changes": [change]} for path in material]
    return _scope_report(
        paths,
        patterns,
        material,
        changes=[owner],
        covered=covered,
        state="attributed",
    )


def official_change_bootstrap_scope_report(
    *,
    official: dict[str, object],
    requested_paths: tuple[str, ...],
) -> dict[str, object]:
    """Admit only official artifacts needed to compile the first Commitment."""
    paths = tuple(dict.fromkeys(filter(None, requested_paths)))
    if not _official_observation_available(official):
        return {}
    change, outputs, next_action = _bootstrap_artifacts(official, paths)
    if not change:
        return {}
    covered = tuple(path for path in paths if _official_artifact_path(path, outputs))
    uncovered = tuple(path for path in paths if path not in covered)
    gaps = [f"openspec_material_path_uncovered:{path}" for path in uncovered]
    report = _scope_report(
        paths,
        (),
        paths,
        changes=[{"name": change, "path": active_change_root(change)}],
        covered=[{"path": path, "changes": [change]} for path in covered],
        state="official_change_bootstrap",
        gaps=gaps,
    )
    report["authorized_paths"] = list(outputs)
    report["next_action"] = next_action
    return report


def _official_observation_available(official: dict[str, object]) -> bool:
    cli = official.get("official_cli")
    commands = official.get("commands")
    if not isinstance(cli, dict) or cli.get("available") is not True:
        return False
    if not isinstance(commands, dict):
        return False
    listed = commands.get("list")
    return bool(
        isinstance(listed, dict)
        and listed.get("exit_code") == 0
        and not listed.get("parse_error")
        and isinstance(listed.get("json"), dict)
    )


def _bootstrap_artifacts(
    official: dict[str, object], paths: tuple[str, ...]
) -> tuple[str, tuple[str, ...], str]:
    active = _active_bootstrap_artifacts(official)
    if active is not None:
        return active
    return _new_change_metadata_artifact(official, paths)


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
    root = active_change_root(change)
    outputs = [f"{root}/.openspec.yaml"]
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
        outputs.append(f"{root}/{output}")
        if not ready and status == "ready":
            ready = identifier
    return (
        change,
        tuple(dict.fromkeys(outputs)),
        (
            f"openspec instructions {ready} --change {change} --json"
            if ready
            else f"openspec status --change {change} --json"
        ),
    )


def _new_change_metadata_artifact(
    official: dict[str, object], paths: tuple[str, ...]
) -> tuple[str, tuple[str, ...], str]:
    commands = official.get("commands")
    listed = commands.get("list") if isinstance(commands, dict) else None
    payload = listed.get("json") if isinstance(listed, dict) else None
    changes = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(changes, list) or changes:
        return "", (), ""
    metadata = tuple(path for path in paths if path.endswith("/.openspec.yaml"))
    if len(paths) != 1 or len(metadata) != 1:
        return "", (), ""
    parts = metadata[0].split("/")
    if len(parts) != 4 or parts[:2] != ["openspec", "changes"]:
        return "", (), ""
    change = parts[2]
    if change == "archive" or logical_change_identifier_issue(change):
        return "", (), ""
    return (
        change,
        (metadata[0],),
        f"openspec new change {change} --json",
    )


def _official_artifact_path(path: str, outputs: tuple[str, ...]) -> bool:
    return any(repository_path_matches(path, output) for output in outputs)


def _scope_inputs(
    root: Path, changed_paths: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], bool]:
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    policy = profile.declaration.openspec if profile.declaration else None
    patterns = policy.material_paths if policy else ()
    material = tuple(
        path for path in paths if any(repository_path_matches(path, glob) for glob in patterns)
    )
    return paths, patterns, material, policy is not None


def _scope_report(
    paths: tuple[str, ...],
    patterns: tuple[str, ...],
    material: tuple[str, ...],
    *,
    changes: list[dict[str, object]] | None = None,
    covered: list[dict[str, object]] | None = None,
    state: str,
    gaps: list[str] | None = None,
) -> dict[str, object]:
    required = gaps or []
    return {
        "verdict": "block" if required else "pass",
        "state": state,
        "changed_paths": list(paths),
        "material_patterns": list(patterns),
        "material_paths": list(material),
        "changes": changes or [],
        "covered_paths": covered or [],
        "uncovered_paths": [] if covered else list(material),
        "required_gaps": required,
        "advisory_gaps": [],
    }
