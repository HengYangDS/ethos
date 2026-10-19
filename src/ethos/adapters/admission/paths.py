"""Observe and classify exact write paths without authorizing repository effects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.patch_admission import projection_preimages
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ignored_paths
from ethos.adapters.repo.git_attributes import received_paths
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES
from ethos.repository.paradigm.report import paradigm_path_gaps
from ethos.repository.policy.projections import observe_projections
from ethos.repository.policy.projections import projection_relations

if TYPE_CHECKING:
    from pathlib import Path


def has_invalid_path_character(text: str) -> bool:
    """A path argument is one literal name; printable spaces are not token separators."""
    return any(not character.isprintable() for character in text)


def check_write_paths(
    root: Path,
    paths: list[Path],
    role: str,
    *,
    effect_report: dict[str, object] | None = None,
) -> tuple[list[dict[str, object]], str]:
    """Observe ownership once per request, preserving unavailable declarations."""
    effects = None
    origin_gap = ""
    if effect_report is not None:
        declared = effect_report.get("origin_outputs", [])
        outputs = {str(path) for path in declared} if isinstance(declared, list) else set()
        effects = effect_report.get("effects") if effect_report.get("index_tree") else None
    else:
        try:
            committed = projection_relations(
                projection_preimages(root, git_stdout(root, "rev-parse", "HEAD"))
            )
            outputs = {item.output for item in (*committed, *observe_projections(root))}
        except (OSError, UnicodeError, ValueError) as exc:
            outputs = set()
            origin_gap = f"projection_ownership_unknown:{exc}"
    indexed = effects if isinstance(effects, dict) else None
    checked = [
        _check_path(root=root, path=path, role=role, outputs=outputs, indexed_effects=indexed)
        for path in paths
    ]
    relative = tuple(
        dict.fromkeys(str(item["relative_path"]) for item in checked if item["relative_path"])
    )
    created = (
        tuple(path for path in relative if indexed.get(path) == "create")
        if indexed is not None
        else tuple(
            str(item["relative_path"])
            for item in checked
            if item["relative_path"] and item["existence"] == "absent"
        )
    )
    received = received_paths(root, created)
    try:
        ignored = frozenset() if indexed is not None else ignored_paths(root, relative)
    except (OSError, ValueError) as error:
        return checked, origin_gap or f"prewrite_ignore_observation_unavailable:{error}"
    for index, path in enumerate(paths):
        relative_path = str(checked[index]["relative_path"])
        if relative_path in ignored or relative_path in received:
            checked[index] = _check_path(
                root=root,
                path=path,
                role=role,
                outputs=outputs,
                indexed_effects=indexed,
                ignored=relative_path in ignored,
                received=relative_path in received,
            )
    return checked, origin_gap


def _check_path(
    *,
    root: Path,
    path: Path,
    role: str,
    outputs: set[str],
    indexed_effects: dict[str, object] | None = None,
    ignored: bool = False,
    received: bool = False,
) -> dict[str, object]:
    text = path.as_posix()
    if has_invalid_path_character(text):
        return _path_report(text, reason="path_invalid_control_character")
    root_path = root.resolve()
    candidate = path if path.is_absolute() else root_path / path
    resolved = candidate if indexed_effects is not None else candidate.resolve()
    if indexed_effects is not None and ".." in resolved.parts:
        return _path_report(resolved.as_posix(), reason="path_outside_worktree")
    try:
        relative = resolved.relative_to(root_path).as_posix()
    except ValueError:
        return _path_report(resolved.as_posix(), reason="path_outside_worktree")
    topology = path_policy_from_declaration(
        relative,
        load_generated_artifact_topology_declaration(),
        origin="projection" if relative in outputs else "unclassified",
    )
    present = (
        relative in indexed_effects and indexed_effects[relative] != "delete"
        if indexed_effects is not None
        else resolved.exists()
    )
    observed = {
        "origin": topology["origin"],
        "existence": "present" if present else "absent",
        "placement": topology["decision"],
    }
    tracked = not ignored
    created = (
        indexed_effects.get(relative) == "create" if indexed_effects is not None else not present
    )
    decision: dict[str, object] = {}
    if topology["decision"] == "deny":
        reason = str(topology.get("required_gap") or "generated_artifact_topology_denied")
    elif created and tracked and (paradigm := paradigm_path_gaps(relative, received=received)):
        reason, decision["repair"] = paradigm[0].required_gap, paradigm[0].repair
    else:
        protected = role in PROTECTED_WRITE_ROLES and tracked
        reason = "protected_lane_tracked_write" if protected else "allowed"
        decision["allowed"] = not protected
    return _path_report(
        resolved.as_posix(),
        relative_path=relative,
        **observed,
        ignored=ignored,
        tracked_candidate=tracked,
        reason=reason,
        **decision,
    )


def _path_report(path: str, *, reason: str, **details: object) -> dict[str, object]:
    return {
        "path": path,
        "relative_path": "",
        "ignored": False,
        "tracked_candidate": False,
        "allowed": False,
        "reason": reason,
        **details,
    }
