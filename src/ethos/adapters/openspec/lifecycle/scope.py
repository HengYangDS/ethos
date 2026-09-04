"""Attribute material changed paths to the selected official OpenSpec Change."""

from __future__ import annotations

import shlex
from pathlib import PurePosixPath
from stat import S_ISREG
from typing import TYPE_CHECKING

from ethos.contracts.semantic import Commitment
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
    root: Path,
    official: dict[str, object],
    requested_paths: tuple[str, ...],
) -> dict[str, object]:
    """Admit only official artifacts needed to compile the first Commitment."""
    paths = tuple(dict.fromkeys(filter(None, requested_paths)))
    if not _official_observation_available(official):
        return {}
    intent = _new_change_root_intent(root, official, paths)
    if intent:
        metadata = f"{active_change_root(intent)}/.openspec.yaml"
        resolved = root.resolve().as_posix()
        report = _scope_report(
            paths,
            (),
            paths,
            changes=[{"name": intent, "path": active_change_root(intent)}],
            uncovered=list(paths),
            state="official_change_bootstrap_intent",
            gaps=[f"openspec_change_metadata_prewrite_required:{intent}"],
        )
        report["next_action"] = (
            f"ethos lane prewrite --paths {shlex.quote(metadata)} "
            f"--editor-root {shlex.quote(resolved)} --require-editor-root "
            f"--root {shlex.quote(resolved)} --json"
        )
        return report
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


def official_validation_repair_scope_report(
    *,
    root: Path,
    official: dict[str, object],
    official_artifact_paths: tuple[str, ...],
    requested_paths: tuple[str, ...],
) -> dict[str, object]:
    """Admit exact official files named by current strict validation failures."""
    paths = tuple(dict.fromkeys(filter(None, requested_paths)))
    if not paths or not _official_observation_available(official):
        return {}
    change = str(official.get("change") or "")
    if logical_change_identifier_issue(change):
        return {}
    state = "canonical_spec_repair"
    repair_paths = (
        _canonical_spec_repair_paths(official)
        if _canonical_spec_repair_context_valid(official, change=change)
        else ()
    )
    if not repair_paths:
        state = "official_change_validation_repair"
        repair_paths = _active_change_validation_repair_paths(
            root,
            official,
            change=change,
            official_artifact_paths=official_artifact_paths,
        )
    if not repair_paths:
        return {}
    covered = tuple(path for path in paths if path in repair_paths)
    uncovered = tuple(path for path in paths if path not in repair_paths)
    gaps = [f"openspec_material_path_uncovered:{path}" for path in uncovered]
    report = _scope_report(
        paths,
        (),
        paths,
        changes=[{"name": change, "path": active_change_root(change)}],
        covered=[{"path": path, "changes": [change]} for path in covered],
        uncovered=list(uncovered),
        state=state,
        gaps=gaps,
    )
    report["authorized_paths"] = list(repair_paths)
    report["next_action"] = "openspec validate --all --strict --json"
    return report


def _active_change_validation_repair_paths(
    root: Path,
    official: dict[str, object],
    *,
    change: str,
    official_artifact_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Resolve strict-blocking issue paths to unique existing official outputs."""
    if not _active_change_validation_repair_context_valid(official, change=change):
        return ()
    item = _selected_failed_change_validation_item(official, change=change)
    issue_paths = _strict_blocking_issue_paths(item)
    if issue_paths is None:
        return ()
    change_root = active_change_root(change)
    outputs = {
        path
        for path in official_artifact_paths
        if repository_path_matches(path, f"{change_root}/**") and _is_regular_file(root / path)
    }
    metadata = f"{change_root}/.openspec.yaml"
    if _is_regular_file(root / metadata):
        outputs.add(metadata)
    return _resolved_issue_repairs(change_root, issue_paths, outputs)


def _selected_failed_change_validation_item(
    official: dict[str, object], *, change: str
) -> dict[str, object] | None:
    """Return the one invalid validator item for the selected active Change."""
    commands = official.get("commands")
    validate = commands.get("validate") if isinstance(commands, dict) else None
    payload = validate.get("json") if isinstance(validate, dict) else None
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    matching = [
        item
        for item in items
        if isinstance(item, dict)
        if item.get("type") == "change" and item.get("id") == change and item.get("valid") is False
    ]
    return matching[0] if len(matching) == 1 else None


def _strict_blocking_issue_paths(item: dict[str, object] | None) -> tuple[str, ...] | None:
    """Return file paths from ERROR/WARNING issues while ignoring INFO guidance."""
    issues = item.get("issues") if item is not None else None
    if not isinstance(issues, list) or not issues:
        return None
    paths: list[str] = []
    for issue in issues:
        if not isinstance(issue, dict):
            return None
        level = issue.get("level")
        if level == "INFO":
            continue
        if level not in {"ERROR", "WARNING"}:
            return None
        issue_path = _strict_relative_issue_path(issue.get("path"))
        if issue_path is None:
            return None
        paths.append(issue_path)
    return tuple(paths) or None


def _resolved_issue_repairs(
    change_root: str,
    issue_paths: tuple[str, ...],
    official_outputs: set[str],
) -> tuple[str, ...]:
    """Resolve every validator path against the two official path bases."""
    repairs: list[str] = []
    for issue_path in issue_paths:
        candidates = {
            f"{change_root}/{issue_path}",
            f"{change_root}/specs/{issue_path}",
        }
        matches = candidates & official_outputs
        if len(matches) != 1:
            return ()
        repairs.extend(matches)
    return tuple(dict.fromkeys(repairs))


def _active_change_validation_repair_context_valid(
    official: dict[str, object], *, change: str
) -> bool:
    """Require one complete selected Change and one readable failed validation."""
    validation_gap = f"openspec_validation_failed:change:{change}"
    permitted_gaps = {
        validation_gap,
        f"commitment_invalid:{change}",
    }
    gaps = string_sequence(official.get("required_gaps"))
    if validation_gap not in gaps or any(gap not in permitted_gaps for gap in gaps):
        return False
    lifecycle = official.get("lifecycle")
    changes = lifecycle.get("changes") if isinstance(lifecycle, dict) else None
    if not isinstance(changes, list) or len(changes) != 1 or not isinstance(changes[0], dict):
        return False
    selected = changes[0]
    artifacts = selected.get("artifacts")
    if not (
        selected.get("name") == change
        and not string_sequence(selected.get("required_gaps"))
        and isinstance(artifacts, list)
        and artifacts
        and all(
            isinstance(artifact, dict) and artifact.get("status") in {"done", "skipped"}
            for artifact in artifacts
        )
    ):
        return False
    commands = official.get("commands")
    status = commands.get("status") if isinstance(commands, dict) else None
    validate = commands.get("validate") if isinstance(commands, dict) else None
    status_payload = status.get("json") if isinstance(status, dict) else None
    validate_payload = validate.get("json") if isinstance(validate, dict) else None
    return bool(
        isinstance(status, dict)
        and status.get("exit_code") == 0
        and not status.get("parse_error")
        and isinstance(status_payload, dict)
        and status_payload.get("changeName") == change
        and isinstance(validate, dict)
        and validate.get("exit_code") == 1
        and not validate.get("parse_error")
        and isinstance(validate_payload, dict)
    )


def _strict_relative_issue_path(value: object) -> str | None:
    """Return one canonical POSIX-relative validator path, or fail closed."""
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        return None
    path = PurePosixPath(value)
    canonical = path.as_posix()
    invalid_part = any(part in {"", ".", ".."} for part in path.parts)
    if path.is_absolute() or canonical != value or invalid_part:
        return None
    return canonical


def _is_regular_file(path: Path) -> bool:
    """Return whether the exact path is a regular file without following a link."""
    try:
        return S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _canonical_spec_repair_context_valid(official: dict[str, object], *, change: str) -> bool:
    """Require one valid selected Change and no non-repair governance gap."""
    prefix = "openspec_validation_failed:spec:"
    gaps = string_sequence(official.get("required_gaps"))
    if not gaps or any(not gap.startswith(prefix) for gap in gaps):
        return False
    projected = official.get("commitment")
    if not isinstance(projected, dict):
        return False
    try:
        commitment = Commitment.model_validate(projected)
    except ValueError:
        return False
    if commitment.id != f"change:{change}":
        return False
    lifecycle = official.get("lifecycle")
    changes = lifecycle.get("changes") if isinstance(lifecycle, dict) else None
    if not isinstance(changes, list) or len(changes) != 1 or not isinstance(changes[0], dict):
        return False
    selected = changes[0]
    artifacts = selected.get("artifacts")
    return bool(
        selected.get("name") == change
        and not string_sequence(selected.get("required_gaps"))
        and isinstance(artifacts, list)
        and artifacts
        and all(
            isinstance(artifact, dict) and artifact.get("status") in {"done", "skipped"}
            for artifact in artifacts
        )
    )


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


def _canonical_spec_repair_paths(official: dict[str, object]) -> tuple[str, ...]:
    prefix = "openspec_validation_failed:spec:"
    capabilities = (
        gap.removeprefix(prefix)
        for gap in string_sequence(official.get("required_gaps"))
        if gap.startswith(prefix)
    )
    valid = (
        capability
        for capability in capabilities
        if capability
        and all(not logical_change_identifier_issue(part) for part in capability.split("/"))
    )
    return tuple(dict.fromkeys(f"openspec/specs/{capability}/spec.md" for capability in valid))


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


def _new_change_root_intent(root: Path, official: dict[str, object], paths: tuple[str, ...]) -> str:
    commands = official.get("commands")
    listed = commands.get("list") if isinstance(commands, dict) else None
    payload = listed.get("json") if isinstance(listed, dict) else None
    changes = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(changes, list) or changes or len(paths) != 1:
        return ""
    parts = paths[0].rstrip("/").split("/")
    if len(parts) != 3 or parts[:2] != ["openspec", "changes"]:
        return ""
    change = parts[2]
    invalid = (
        change == "archive" or logical_change_identifier_issue(change) or (root / paths[0]).exists()
    )
    return "" if invalid else change


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
    uncovered: list[str] | None = None,
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
        "uncovered_paths": uncovered
        if uncovered is not None
        else ([] if covered else list(material)),
        "required_gaps": required,
        "advisory_gaps": [],
    }
