"""Documentation registry health checks."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from markdown_it import MarkdownIt

from ethos.contracts.verdict import close_verdict
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.registry.docs.links import markdown_links
from ethos.repository.registry.docs.registry import DEFAULT_ALLOWED_STATES
from ethos.repository.registry.docs.registry import REQUIRED_FIELDS
from ethos.repository.registry.docs.registry import VISIBLE_SECTION_LABELS
from ethos.repository.registry.docs.registry import allowed_roles
from ethos.repository.registry.docs.registry import allowed_states
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.repository.registry.docs.registry import docs_root

if TYPE_CHECKING:
    from collections.abc import Callable

ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
OBSERVATIONAL_ROLES = frozenset({"evidence", "history"})


def docs_health_report(
    root: Path,
    *,
    command_validator: Callable[[list[str]], str] | None = None,
) -> dict[str, object]:
    """Report docs metadata, structure, and live-command-example health."""
    try:
        root = root.resolve()
        registry = build_docs_registry(root)
        states = allowed_states(root)
        roles = allowed_roles(root)
    except ValueError as exc:
        gap = str(exc)
        if gap != INVALID_PROFILE_ERROR and not gap.startswith(
            ("docs_taxonomy_invalid:", "docs_metadata_invalid:")
        ):
            raise
        return empty_docs_health_report(gap)
    missing = [
        entry["path"]
        for entry in registry
        if any(
            field not in entry or (field != "relations" and not entry[field])
            for field in REQUIRED_FIELDS
        )
    ]
    invalid_state = [
        f"invalid_state:{entry['path']}:{entry['state']}"
        for entry in registry
        if states and entry.get("state", "") and entry.get("state", "") not in states
    ]
    invalid_role = [
        f"invalid_role:{entry['path']}:{entry['role']}"
        for entry in registry
        if roles and entry.get("role", "") and entry.get("role", "") not in roles
    ]
    subject_paths: dict[str, list[str]] = {}
    for entry in registry:
        if entry.get("subject", ""):
            subject_paths.setdefault(entry.get("subject", ""), []).append(entry["path"])
    duplicate_subjects = [
        f"duplicate_subject:{subject}:{','.join(paths)}"
        for subject, paths in sorted(subject_paths.items())
        if len(paths) > 1
    ]
    visible_section_gaps = visible_section_gaps_for_registry(root, registry)
    invalid_command_examples = (
        command_example_gaps(root, registry, command_validator) if command_validator else []
    )
    unindexed_plans = plan_index_gaps(root, registry)
    readme_disposition = readme_disposition_gaps(root, registry)
    required_gaps = (
        missing
        + invalid_state
        + invalid_role
        + duplicate_subjects
        + visible_section_gaps
        + invalid_command_examples
        + unindexed_plans
        + readme_disposition
        + relation_gaps(root, registry)
    )
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required_gaps)),
        "document_count": len(registry),
        "missing_metadata": missing,
        "invalid_state": invalid_state,
        "invalid_role": invalid_role,
        "duplicate_subjects": duplicate_subjects,
        "missing_visible_sections": visible_section_gaps,
        "invalid_command_examples": invalid_command_examples,
        "unindexed_plans": unindexed_plans,
        "readme_disposition": readme_disposition,
        "required_gaps": required_gaps,
        "registry": registry,
    }


def empty_docs_health_report(gap: str) -> dict[str, object]:
    """Return the stable fail-closed shape for an unreadable registry declaration."""
    return {
        "verdict": "block",
        "document_count": 0,
        "missing_metadata": [],
        "invalid_state": [],
        "invalid_role": [],
        "duplicate_subjects": [],
        "missing_visible_sections": [],
        "invalid_command_examples": [],
        "unindexed_plans": [],
        "readme_disposition": [],
        "required_gaps": [gap],
        "registry": [],
    }


def plan_index_gaps(root: Path, registry: list[dict[str, Any]]) -> list[str]:
    """Return active or planned documents absent from the plan index."""
    docs = docs_root(root)
    docs_prefix = docs.relative_to(root).as_posix().rstrip("/")
    plans_prefix = f"{docs_prefix}/plans/"
    index = docs / "plans" / "README.md"
    if not index.exists():
        return []
    indexed = {
        (index.parent / target.partition("#")[0]).resolve()
        for _lineno, target in markdown_links(index)
        if target.partition("#")[0].endswith(".md")
    }
    return [
        f"unindexed_plan:{entry['path']}"
        for entry in registry
        if entry["path"].startswith(plans_prefix)
        and entry["path"] != f"{plans_prefix}README.md"
        and entry.get("role", "") == "plan"
        and entry.get("state", "") in {"active", "planned"}
        and (root / entry["path"]).resolve() not in indexed
    ]


def readme_disposition_gaps(root: Path, registry: list[dict[str, Any]]) -> list[str]:
    """Require a real directory entrance and reject inert README markers."""
    docs = docs_root(root)
    by_parent: dict[Path, set[Path]] = {}
    sources = [root / entry["path"] for entry in registry]
    sources.extend(
        path for path in docs.rglob("*.toml") if path.is_file() and not path.is_symlink()
    )
    for source in sources:
        parent = source.parent
        by_parent.setdefault(parent, set()).add(source)
        while parent != docs:
            by_parent.setdefault(parent.parent, set()).add(parent)
            parent = parent.parent
    gaps: list[str] = []
    for directory, entries in sorted(by_parent.items()):
        children = entries - {directory / "README.md"}
        if len(children) >= 2 and not (directory / "README.md").is_file():
            relative = (directory / "README.md").relative_to(root).as_posix()
            gaps.append(f"docs_readme_missing:{relative}")
    for entry in registry:
        if Path(entry["path"]).name != "README.md":
            continue
        path = root / entry["path"]
        children = by_parent.get(path.parent, set()) - {path}
        if not children:
            gaps.append(f"docs_readme_without_children:{entry['path']}")
        elif not any(
            (target := link.partition("#")[0].partition("?")[0])
            and not target.startswith(("/", "http:", "https:", "mailto:"))
            and any(
                (resolved := (path.parent / target).resolve()) == child
                or (child.is_dir() and resolved.is_relative_to(child))
                for child in children
            )
            for _line, link in markdown_links(path)
        ):
            gaps.append(f"docs_readme_without_local_route:{entry['path']}")
    return gaps


def visible_section_gaps_for_registry(root: Path, registry: list[dict[str, Any]]) -> list[str]:
    """Return missing visible-section gaps for active/canonical docs."""
    gaps: list[str] = []
    for entry in registry:
        if not requires_visible_sections(entry):
            continue
        path = root / entry["path"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        body = text.split("\n---", 1)[1] if text.startswith("---\n") else text
        paragraphs = [
            token.content
            for token in MarkdownIt("commonmark").parse(body)
            if token.type == "inline"
        ]
        gaps.extend(
            f"missing_visible_section:{entry['path']}:{label[:-1].lower()}"
            for label in VISIBLE_SECTION_LABELS
            if not any(
                paragraph.startswith(label) and paragraph.removeprefix(label).strip()
                for paragraph in paragraphs
            )
        )
        for paragraph in paragraphs:
            if paragraph.startswith("Status:"):
                visible = paragraph.removeprefix("Status:").strip().partition(" ")[0].rstrip(".;,")
                if visible in DEFAULT_ALLOWED_STATES and visible != entry.get("state"):
                    gaps.append(f"docs_visible_state_conflict:{entry['path']}:{visible}")
    return gaps


def requires_visible_sections(entry: dict[str, Any]) -> bool:
    """Return whether a registry entry must expose visible docs sections."""
    return (
        entry.get("state", "") in {"canonical", "active"}
        and entry.get("role", "") not in OBSERVATIONAL_ROLES
    )


def command_example_gaps(
    root: Path,
    registry: list[dict[str, Any]],
    command_validator: Callable[[list[str]], str],
) -> list[str]:
    """Return active-doc examples absent from the live Cyclopts operation tree."""
    active_paths = {entry["path"] for entry in registry if requires_visible_sections(entry)}
    gaps: list[str] = []
    for relative_path in sorted(active_paths):
        path = root / relative_path
        for lineno, command in shell_commands(path):
            if (tokens := ethos_command_tokens(command)) and (invalid := command_validator(tokens)):
                gaps.append(f"unknown_ethos_command_example:{relative_path}:{lineno}:{invalid}")
    return gaps


def shell_commands(path: Path) -> list[tuple[int, str]]:
    """Extract logical commands from shell fenced blocks."""
    commands: list[tuple[int, str]] = []
    in_shell = False
    buffer: list[str] = []
    start_lineno = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_shell and buffer:
                commands.append((start_lineno, " ".join(buffer)))
                buffer = []
            in_shell = stripped in {"```bash", "```sh"} if not in_shell else False
            continue
        if not in_shell or not stripped or stripped.startswith("#"):
            continue
        if not buffer:
            start_lineno = lineno
        continued = stripped.endswith("\\")
        buffer.append(stripped[:-1].rstrip() if continued else stripped)
        if not continued:
            commands.append((start_lineno, " ".join(buffer)))
            buffer = []
    if in_shell and buffer:
        commands.append((start_lineno, " ".join(buffer)))
    return commands


def ethos_command_tokens(command: str) -> list[str]:
    """Return an example's ETHOS argv, excluding its executable token."""
    try:
        command_tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        command_tokens = command.split()
    if command_tokens[:1] == ["env"]:
        command_tokens = command_tokens[1:]
    while command_tokens and ENV_ASSIGNMENT.match(command_tokens[0]):
        command_tokens = command_tokens[1:]
    if command_tokens[:1] == ["ethos"]:
        return command_tokens[1:]
    if command_tokens[:2] == ["uv", "run"]:
        indices = [
            index
            for index, argument in enumerate(command_tokens[2:], start=2)
            if argument == "ethos"
        ]
        return command_tokens[indices[-1] + 1 :] if indices else []
    if command_tokens[:3] == ["python", "-m", "ethos.cli"]:
        return command_tokens[3:]
    return []


def relation_gaps(root: Path, registry: list[dict[str, Any]]) -> list[str]:
    """Resolve local authority and containment references without guessing scope prose."""
    required = {"current_owner", "projects", "derives", "derives_from", "constrained_by", "part_of"}
    subjects = {entry["subject"] for entry in registry if entry.get("subject")}
    gaps = []
    for entry in registry:
        for relation, value in entry.get("relations", {}).items():
            if relation not in required:
                continue
            for target in value if isinstance(value, list) else [value]:
                if target in subjects or "://" in target:
                    continue
                path = target.partition("#")[0]
                resolved = (root / entry["path"]).parent / path
                if not path or not resolved.is_file():
                    gaps.append(f"docs_relation_target_missing:{entry['path']}:{relation}:{target}")
    return gaps
