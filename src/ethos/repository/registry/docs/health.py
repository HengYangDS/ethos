"""Documentation registry health checks."""

from __future__ import annotations

import re
import shlex
from itertools import pairwise
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any

from markdown_it import MarkdownIt

from ethos.contracts.verdict import close_verdict
from ethos.repository.policy.projections import observe_projections
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.registry.docs.links import markdown_links
from ethos.repository.registry.docs.registry import DEFAULT_ALLOWED_STATES
from ethos.repository.registry.docs.registry import REQUIRED_FIELDS
from ethos.repository.registry.docs.registry import allowed_roles
from ethos.repository.registry.docs.registry import allowed_states
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.repository.registry.docs.registry import docs_root
from ethos.repository.release.configuration import RELEASE_HISTORY_FILE

if TYPE_CHECKING:
    from collections.abc import Callable

ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
OBSERVATIONAL_ROLES = frozenset({"evidence", "history"})
MAX_CURRENT_MARKDOWN_NONBLANK = 500
_RELEASE_HEADING = re.compile(r"^\[[^\[\]\n]+\](?: - \d{4}-\d{2}-\d{2})?$")


def docs_health_report(
    root: Path,
    *,
    command_validator: Callable[[list[str]], str] | None = None,
    tracked_documents: tuple[str, ...] = (),
) -> dict[str, object]:
    """Report docs metadata, structure, and live-command-example health."""
    root = root.resolve()
    try:
        generated_outputs = frozenset(item.output for item in observe_projections(root))
        registry = build_docs_registry(root, generated_outputs=generated_outputs)
        states = allowed_states(root)
        roles = allowed_roles(root)
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
        length_gaps = current_document_length_gaps(
            root, registry, generated_outputs, tracked_documents
        )
        required_gaps = (
            missing
            + invalid_state
            + invalid_role
            + duplicate_subjects
            + visible_section_gaps
            + invalid_command_examples
            + unindexed_plans
            + readme_disposition
            + length_gaps
            + relation_gaps(root, registry)
        )
    except ValueError as exc:
        gap = str(exc)
        if gap != INVALID_PROFILE_ERROR and not gap.startswith(
            ("docs_taxonomy_invalid:", "docs_metadata_invalid:", "projection_")
        ):
            raise
        return empty_docs_health_report(gap)
    except OSError as exc:
        if not exc.filename:
            raise
        source = Path(exc.filename).resolve()
        if source.suffix != ".md" or not source.is_relative_to(docs_root(root)):
            raise
        return empty_docs_health_report(
            f"docs_source_unavailable:{source.relative_to(root).as_posix()}"
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


def current_document_length_gaps(
    root: Path,
    registry: list[dict[str, Any]],
    generated_outputs: frozenset[str],
    tracked_documents: tuple[str, ...],
) -> list[str]:
    """Bound authored Markdown, not official intent or owned generated output."""
    paths = set(tracked_documents) | {str(entry["path"]) for entry in registry}
    gaps: list[str] = []
    for relative in sorted(paths - generated_outputs):
        if _official_openspec_carrier(relative):
            continue
        path = root / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            gaps.append(f"docs_source_unavailable:{relative}")
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            count = sum(bool(line.strip()) for line in lines)
            if relative == RELEASE_HISTORY_FILE and count > MAX_CURRENT_MARKDOWN_NONBLANK:
                count = _release_history_max_section(lines) or count
        except (OSError, UnicodeError):
            gaps.append(f"docs_source_unavailable:{relative}")
            continue
        if count > MAX_CURRENT_MARKDOWN_NONBLANK:
            gaps.append(f"docs_length_exceeded:{relative}:{count}>{MAX_CURRENT_MARKDOWN_NONBLANK}")
    return gaps


def _release_history_max_section(lines: list[str]) -> int | None:
    """Bound navigable release sections without shortening history."""
    tokens = MarkdownIt("commonmark").parse("\n".join(lines))
    title = ""
    sections: list[tuple[int, str]] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        content = tokens[index + 1].content.strip()
        if token.tag == "h1" and not title:
            title = content
        elif token.tag == "h2":
            sections.append((token.map[0], content))
    if (
        not title.casefold().endswith("changelog")
        or len(sections) < 2
        or sections[0][1].casefold() != "[unreleased]"
        or any(not _RELEASE_HEADING.fullmatch(heading) for _, heading in sections)
    ):
        return None
    boundaries = [0, *(line for line, _ in sections), len(lines)]
    return max(
        sum(bool(line.strip()) for line in lines[start:end]) for start, end in pairwise(boundaries)
    )


def _official_openspec_carrier(relative: str) -> bool:
    """Keep the native spec-driven artifact roots outside document length policy."""
    parts = PurePosixPath(relative).parts
    if parts[:3] == ("openspec", "changes", "archive"):
        return True
    if len(parts) == 4 and parts[:2] == ("openspec", "specs"):
        return parts[3] == "spec.md"
    if len(parts) == 4 and parts[:2] == ("openspec", "changes"):
        return parts[3] in {"proposal.md", "design.md", "tasks.md"}
    return (
        len(parts) == 6
        and parts[:2] == ("openspec", "changes")
        and parts[3] == "specs"
        and parts[5] == "spec.md"
    )


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
    """Require readable content without imposing ETHOS-specific prose labels."""
    gaps: list[str] = []
    for entry in registry:
        path = root / entry["path"]
        text = path.read_text(encoding="utf-8")
        commented = text.startswith("<!--\n")
        reader_guidance = requires_reader_guidance(entry)
        if not commented and not reader_guidance:
            continue
        body = text.split("\n---", 1)[1] if text.startswith("---\n") else text
        tokens = MarkdownIt("commonmark").parse(body)
        if commented and (
            len(tokens) < 2
            or tokens[0].type != "html_block"
            or tokens[1].type != "heading_open"
            or tokens[1].tag != "h1"
        ):
            gaps.append(f"docs_title_not_first:{entry['path']}")
        if not reader_guidance:
            continue
        if not any(token.type == "heading_open" and token.tag == "h1" for token in tokens):
            gaps.append(f"docs_visible_title_missing:{entry['path']}")
        paragraphs = [
            token.content
            for index, token in enumerate(tokens)
            if token.type == "inline" and (index == 0 or tokens[index - 1].type != "heading_open")
        ]
        if not any(paragraph.strip() for paragraph in paragraphs):
            gaps.append(f"docs_visible_guidance_missing:{entry['path']}")
        gaps.extend(_visible_state_gaps(paragraphs, entry))
    return gaps


def _visible_state_gaps(paragraphs: list[str], entry: dict[str, Any]) -> list[str]:
    """Keep an authored status claim consistent with its structured state."""
    gaps = []
    for paragraph in paragraphs:
        if not paragraph.startswith("Status:"):
            continue
        statement = paragraph.removeprefix("Status:").strip()
        if not statement:
            gaps.append(f"docs_visible_status_empty:{entry['path']}")
            continue
        visible = statement.partition(" ")[0].rstrip(".;,")
        if visible in DEFAULT_ALLOWED_STATES and visible != entry.get("state"):
            gaps.append(f"docs_visible_state_conflict:{entry['path']}:{visible}")
    return gaps


def requires_reader_guidance(entry: dict[str, Any]) -> bool:
    """Return whether an active document needs title and visible reader guidance."""
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
    active_paths = {entry["path"] for entry in registry if requires_reader_guidance(entry)}
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
