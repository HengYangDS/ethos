"""Require the selected Change to archive into strictly valid accepted specifications."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.lifecycle.validation import validation_items
from ethos.adapters.openspec.lifecycle.validation import validation_result_gaps
from ethos.adapters.openspec.projection import openspec_tree_projection
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from pathlib import Path

_SPEC_VALIDATION = ("validate", "--specs", "--strict", "--json")
_REQUIREMENT_PATH = re.compile(r"requirements\[(\d+)\]")


def archive_readiness_gaps(root: Path, *, change: str, tree: str) -> tuple[str, ...]:
    """Archive one active Change on a disposable projection, then validate the specs strictly."""
    if not change or logical_change_identifier_issue(change):
        return ()
    with openspec_tree_projection(root, tree) as projection:
        if not (projection / active_change_root(change)).is_dir():
            return ()
        command = openspec_cli.openspec_base_command(execution_probe=False)
        if command is None:
            return ("openspec_official_cli_missing",)
        archive = openspec_cli.run_json(
            projection, command, openspec_cli.archive_command(projection, change)[1:]
        )
        if openspec_cli.archive_result(projection, change, archive)[0]:
            return (f"openspec_archive_simulation_failed:{change}",)
        validation = openspec_cli.run_json(projection, command, _SPEC_VALIDATION)
        if not validation_result_gaps(validation):
            return ()
        locations = _issue_locations(projection, command, validation["json"])
    return tuple(
        f"openspec_archived_requirement_invalid:{change}:{spec}:{requirement}"
        if requirement
        else f"openspec_archived_spec_invalid:{change}:{spec}"
        for spec, requirement in locations
    ) or (f"openspec_archived_specs_invalid:{change}",)


def _issue_locations(
    projection: Path, command: tuple[str, ...], payload: dict[str, Any]
) -> tuple[tuple[str, str], ...]:
    """Name each archived specification issue by the requirement the official parser reports."""
    locations: dict[tuple[str, str], None] = {}
    names: dict[str, tuple[str, ...]] = {}
    for item in validation_items(payload) or ():
        if not isinstance(item, dict) or item.get("type") != "spec":
            continue
        spec = str(item.get("id") or "")
        issues = [issue for issue in item.get("issues") or () if isinstance(issue, dict)]
        if not issues and item.get("valid") is False:
            locations[spec, ""] = None
        for issue in issues:
            matched = _REQUIREMENT_PATH.match(str(issue.get("path") or ""))
            if matched is None:
                locations[spec, ""] = None
                continue
            if spec not in names:
                names[spec] = _requirement_names(projection, command, spec)
            index = int(matched[1])
            locations[spec, names[spec][index] if index < len(names[spec]) else ""] = None
    return tuple(locations)


def _requirement_names(projection: Path, command: tuple[str, ...], spec: str) -> tuple[str, ...]:
    shown = openspec_cli.run_json(projection, command, ("show", spec, "--type", "spec", "--json"))
    requirements = shown["json"].get("requirements")
    if not isinstance(requirements, list):
        return ()
    return tuple(
        str(requirement.get("name") or "") if isinstance(requirement, dict) else ""
        for requirement in requirements
    )
