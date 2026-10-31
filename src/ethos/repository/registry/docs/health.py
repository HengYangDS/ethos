"""Documentation registry health checks."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import unquote

from markdown_it import MarkdownIt

from ethos.contracts.verdict import close_verdict
from ethos.repository.paradigm.size import repository_ceilings
from ethos.repository.policy.projections import observe_projections
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile
from ethos.repository.registry.docs.decisions import decision_record_gaps
from ethos.repository.registry.docs.links import markdown_links
from ethos.repository.registry.docs.registry import DEFAULT_ALLOWED_STATES
from ethos.repository.registry.docs.registry import REQUIRED_FIELDS
from ethos.repository.registry.docs.registry import allowed_roles
from ethos.repository.registry.docs.registry import allowed_states
from ethos.repository.registry.docs.registry import authored_document_paths
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.repository.registry.docs.registry import docs_root
from ethos.repository.registry.docs.registry import intent_document_owner
from ethos.repository.release.configuration import RELEASE_HISTORY_FILE

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.repository.registry.docs.registry import DocumentOrigins

ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
OBSERVATIONAL_ROLES = frozenset({"evidence", "history"})


def docs_health_report(
    root: Path,
    *,
    command_validator: Callable[[list[str]], str] | None = None,
    tracked_documents: tuple[str, ...] | None = None,
    retained_origins: DocumentOrigins | None = None,
) -> dict[str, object]:
    """Report docs metadata, structure, and live-command-example health."""
    root = root.resolve()
    try:
        generated_outputs = frozenset(item.output for item in observe_projections(root))
        registry = build_docs_registry(
            root,
            generated_outputs=generated_outputs,
            retained_origins=retained_origins,
            selected_documents=tracked_documents,
        )
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
        readme_disposition = readme_disposition_gaps(
            root, registry, generated_outputs=generated_outputs
        )
        decision_identity = decision_record_gaps(root, registry)
        length_gaps = current_document_length_gaps(
            root, registry, generated_outputs, tracked_documents or ()
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
            + decision_identity
            + length_gaps
            + relation_gaps(root, registry)
        )
    except ValueError as exc:
        gap = str(exc)
        if gap != INVALID_PROFILE_ERROR and not gap.startswith(
            (
                "docs_taxonomy_invalid:",
                "docs_metadata_invalid:",
                "docs_source_unavailable:",
                "projection_",
            )
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
    paths = authored_document_paths(registry, tracked_documents, generated_outputs)
    readable = set(paths) | {str(entry["path"]) for entry in registry if entry.get("origin")}
    ceiling = repository_ceilings(root)["document_nonblank_lines"]
    gaps: list[str] = []
    for relative in sorted(readable):
        owner = intent_document_owner(relative)
        if owner == "openspec-history" or (
            owner == "openspec" and relative.startswith("openspec/specs/")
        ):
            continue
        path = root / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            gaps.append(f"docs_source_unavailable:{relative}")
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            gaps.append(f"docs_source_unavailable:{relative}")
            continue
        if relative == RELEASE_HISTORY_FILE or relative not in paths:
            continue
        count = sum(bool(line.strip()) for line in lines)
        if count > ceiling:
            gaps.append(f"docs_length_exceeded:{relative}:{count}>{ceiling}")
    return gaps


def _normative_route_gaps(
    root: Path, registry: list[dict[str, Any]], generated_outputs: frozenset[str]
) -> list[str]:
    """Reach declared current responsibilities through selected authored documents."""
    profile = load_repository_profile(root)
    if profile.declaration is None:
        return []
    docs = docs_root(root)
    required = {
        root / relative
        for relative in profile.declaration.normative_sources
        if (root / relative).is_relative_to(docs)
    }
    documents = {
        root / relative for relative in authored_document_paths(registry, (), generated_outputs)
    }
    pending = [docs / "README.md"]
    reached: set[Path] = set()
    while pending:
        source = pending.pop()
        if source in reached or source not in documents:
            continue
        reached.add(source)
        for _line, link in markdown_links(source):
            target = link.partition("#")[0].partition("?")[0]
            if not target or target.startswith("/") or ":" in target:
                continue
            resolved = (source.parent / unquote(target)).resolve()
            if resolved in documents:
                pending.append(resolved)
            elif resolved / "README.md" in documents:
                pending.append(resolved / "README.md")
    return [
        f"docs_normative_source_unreachable:{path.relative_to(root).as_posix()}"
        for path in sorted(required - reached)
    ]


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


def readme_disposition_gaps(
    root: Path,
    registry: list[dict[str, Any]],
    *,
    generated_outputs: frozenset[str] = frozenset(),
) -> list[str]:
    """Require a real directory entrance and reject inert README markers."""
    docs = docs_root(root)
    authored = set(authored_document_paths(registry, (), generated_outputs))
    by_parent: dict[Path, set[Path]] = {}
    sources = [root / entry["path"] for entry in registry]
    sources.extend(
        path
        for path in docs.rglob("*")
        if path.suffix in {".toml", ".json"} and path.is_file() and not path.is_symlink()
    )
    sources.extend(_linked_metadata_children(root, registry, generated_outputs))
    for source in sources:
        parent = source.parent
        by_parent.setdefault(parent, set()).add(source)
        while parent != docs:
            by_parent.setdefault(parent.parent, set()).add(parent)
            parent = parent.parent
    gaps: list[str] = []
    for directory, entries in sorted(by_parent.items()):
        children = entries - {directory / "README.md"}
        relative = (directory / "README.md").relative_to(root).as_posix()
        if len(children) >= 2 and relative not in authored:
            gaps.append(f"docs_readme_missing:{relative}")
    for entry in registry:
        if entry["path"] not in authored or Path(entry["path"]).name != "README.md":
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
    return gaps + _normative_route_gaps(root, registry, generated_outputs)


def visible_section_gaps_for_registry(root: Path, registry: list[dict[str, Any]]) -> list[str]:
    """Require readable content without imposing ETHOS-specific prose labels."""
    gaps: list[str] = []
    for entry in registry:
        path = root / entry["path"]
        if not requires_reader_guidance(entry):
            continue
        text = path.read_text(encoding="utf-8")
        body = text.split("\n---", 1)[1] if text.startswith("---\n") else text
        tokens = MarkdownIt("commonmark").parse(body)
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
    required = {
        "current_owner",
        "projects",
        "derives",
        "derives_from",
        "constrained_by",
        "part_of",
    }
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


def _linked_metadata_children(
    root: Path, registry: list[dict[str, Any]], generated_outputs: frozenset[str]
) -> list[Path]:
    """Select only actual safe metadata files routed by a directory entrance."""
    sources: list[Path] = []
    for entry in registry:
        readme = root / entry["path"]
        if readme.name != "README.md":
            continue
        for _line, link in markdown_links(readme):
            target = link.partition("#")[0].partition("?")[0]
            if not target or target.startswith("/") or ":" in target:
                continue
            source = readme.parent / target
            resolved = source.resolve()
            if (
                source.suffix in {".json", ".toml", ".yaml", ".yml"}
                and source.is_file()
                and not any(
                    parent.is_symlink()
                    for parent in (source, *source.parents)
                    if parent.is_relative_to(root)
                )
                and resolved.is_relative_to(readme.parent.resolve())
                and resolved.relative_to(root).as_posix() not in generated_outputs
            ):
                sources.append(resolved)
    return sources
