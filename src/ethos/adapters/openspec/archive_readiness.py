"""Require the selected Change to archive into strictly valid accepted specifications."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.lifecycle.validation import validation_items
from ethos.adapters.openspec.lifecycle.validation import validation_result_gaps
from ethos.adapters.openspec.projection import openspec_tree_projection
from ethos.adapters.repo.git import run_git
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.policy.references.markdown import markdown_tokens
from ethos.repository.registry.docs.decisions import DECISION_RECORD_NAME

if TYPE_CHECKING:
    from pathlib import Path

_SPEC_VALIDATION = ("validate", "--specs", "--strict", "--json")
_REQUIREMENT_PATH = re.compile(r"requirements\[(\d+)\]")


def archive_readiness_gaps(root: Path, *, change: str, tree: str) -> tuple[str, ...]:
    """Archive one active Change on a disposable projection, then validate the specs strictly.

    The Change must first cite every decision record of the tree that names it.
    """
    if not change or logical_change_identifier_issue(change):
        return ()
    with openspec_tree_projection(root, tree) as projection:
        artifacts = projection / active_change_root(change)
        if not artifacts.is_dir():
            return ()
        uncited = _uncited_decision_records(root, tree, change, artifacts)
        return (*uncited, *_simulated_archive_gaps(projection, change))


def _uncited_decision_records(
    root: Path, tree: str, change: str, artifacts: Path
) -> tuple[str, ...]:
    """Name each decision record that names the Change in inline code but that it never cites."""
    citing = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(artifacts.rglob("*"))
        if path.is_file()
    )
    listing = run_git(root, "ls-tree", "-r", "-z", "--name-only", tree).stdout.split("\0")
    gaps = []
    # OpenSpec holds Change artifacts and their immutable archive, never decision records.
    for path in sorted(item for item in listing if item and not item.startswith("openspec/")):
        name = PurePosixPath(path).name
        if (record := DECISION_RECORD_NAME.fullmatch(name)) is None:
            continue
        identity = f"DR-{record[1]}"
        named = change in _inline_code(run_git(root, "cat-file", "blob", f"{tree}:{path}").stdout)
        if named and not re.search(rf"\b{identity}\b", citing) and name not in citing:
            gaps.append(f"openspec_decision_uncited:{change}:{identity}")
    return tuple(gaps)


def _inline_code(source: str) -> frozenset[str]:
    """Return the inline code spans of one record's Markdown body."""
    body = source.split("\n---\n", 1)[1] if source.startswith("---\n") else source
    return frozenset(
        child.content
        for token in markdown_tokens(body) or ()
        if token.type == "inline"
        for child in token.children or ()
        if child.type == "code_inline"
    )


def _simulated_archive_gaps(projection: Path, change: str) -> tuple[str, ...]:
    """Archive the Change with the official CLI, then name each strict validation issue."""
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
