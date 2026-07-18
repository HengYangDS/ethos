"""Documentation registry health checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.registry.docs.registry import REQUIRED_FIELDS
from ethos.repository.registry.docs.registry import VISIBLE_SECTION_LABELS
from ethos.repository.registry.docs.registry import allowed_roles
from ethos.repository.registry.docs.registry import allowed_states
from ethos.repository.registry.docs.registry import build_docs_registry

if TYPE_CHECKING:
    from pathlib import Path

OBSERVATIONAL_DOC_PREFIXES = ("evidence/", "docs/archive/")


def docs_health_report(root: Path) -> dict[str, object]:
    """Report docs front matter, taxonomy, duplicate-subject, and visible-section health."""
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
    required_gaps = (
        missing + invalid_state + invalid_role + duplicate_subjects + visible_section_gaps
    )
    return {
        "ok": not required_gaps,
        "document_count": len(registry),
        "missing_metadata": missing,
        "invalid_state": invalid_state,
        "invalid_role": invalid_role,
        "duplicate_subjects": duplicate_subjects,
        "missing_visible_sections": visible_section_gaps,
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
