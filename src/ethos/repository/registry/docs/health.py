"""Documentation registry health checks."""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING

from ethos.repository.registry.docs.links import markdown_paths
from ethos.repository.registry.docs.registry import REQUIRED_FIELDS
from ethos.repository.registry.docs.registry import VISIBLE_SECTION_LABELS
from ethos.repository.registry.docs.registry import allowed_roles
from ethos.repository.registry.docs.registry import allowed_states
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.surface.cli._base import app
from ethos.surface.cli._base import load_command_groups

if TYPE_CHECKING:
    from pathlib import Path

OBSERVATIONAL_DOC_PREFIXES = ("evidence/", "docs/archive/")
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def docs_health_report(root: Path) -> dict[str, object]:
    """Report docs metadata, structure, and live-command-example health."""
    registry = build_docs_registry(root)
    missing = [
        entry["path"] for entry in registry if any(not entry[field] for field in REQUIRED_FIELDS)
    ]
    states = allowed_states(root)
    invalid_state = [
        f"invalid_state:{entry['path']}:{entry['state']}"
        for entry in registry
        if states and entry["state"] and entry["state"] not in states
    ]
    roles = allowed_roles(root)
    invalid_role = [
        f"invalid_role:{entry['path']}:{entry['role']}"
        for entry in registry
        if roles and entry["role"] and entry["role"] not in roles
    ]
    subject_paths: dict[str, list[str]] = {}
    for entry in registry:
        if entry["subject"]:
            subject_paths.setdefault(entry["subject"], []).append(entry["path"])
    duplicate_subjects = [
        f"duplicate_subject:{subject}:{','.join(paths)}"
        for subject, paths in sorted(subject_paths.items())
        if len(paths) > 1
    ]
    visible_section_gaps = visible_section_gaps_for_registry(root, registry)
    invalid_command_examples = command_example_gaps(root, registry)
    required_gaps = (
        missing
        + invalid_state
        + invalid_role
        + duplicate_subjects
        + visible_section_gaps
        + invalid_command_examples
    )
    return {
        "ok": not required_gaps,
        "document_count": len(registry),
        "missing_metadata": missing,
        "invalid_state": invalid_state,
        "invalid_role": invalid_role,
        "duplicate_subjects": duplicate_subjects,
        "missing_visible_sections": visible_section_gaps,
        "invalid_command_examples": invalid_command_examples,
        "required_gaps": required_gaps,
        "registry": registry,
    }


def visible_section_gaps_for_registry(root: Path, registry: list[dict[str, str]]) -> list[str]:
    """Return missing visible-section gaps for active/canonical docs."""
    gaps: list[str] = []
    for entry in registry:
        if not requires_visible_sections(entry):
            continue
        path = root / entry["path"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for label in VISIBLE_SECTION_LABELS:
            if label not in text:
                gaps.append(f"missing_visible_section:{entry['path']}:{label[:-1].lower()}")
    return gaps


def requires_visible_sections(entry: dict[str, str]) -> bool:
    """Return whether a registry entry must expose visible docs sections."""
    if entry["path"].startswith(OBSERVATIONAL_DOC_PREFIXES):
        return False
    return entry["state"] in {"canonical", "active"}


def command_example_gaps(root: Path, registry: list[dict[str, str]]) -> list[str]:
    """Return active-doc examples absent from the live Cyclopts operation tree."""
    active_paths = {entry["path"] for entry in registry if requires_visible_sections(entry)}
    gaps: list[str] = []
    for path in markdown_paths(root):
        relative_path = path.relative_to(root).as_posix()
        if relative_path not in active_paths:
            continue
        for lineno, command in shell_commands(path):
            if (tokens := ethos_command_tokens(command)) and (
                invalid := live_cyclopts_command(tokens)
            ):
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


def live_cyclopts_command(tokens: list[str]) -> str:
    """Return an unknown command path using the loaded Cyclopts operation tree."""
    load_command_groups([])
    command_chain, apps, remaining = app.parse_commands(tokens)
    if not command_chain:
        return " ".join(("ethos", *(token for token in tokens if not token.startswith("-"))))
    if apps[-1].default_command is None and remaining and not remaining[0].startswith("-"):
        return " ".join(("ethos", *command_chain, remaining[0]))
    return ""
