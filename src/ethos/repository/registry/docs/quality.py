"""Composite documentation quality report."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.normalization.core import string_list
from ethos.repository.registry.docs.commands import command_examples_report
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.links import glossary_report
from ethos.repository.registry.docs.links import link_integrity_report
from ethos.repository.registry.docs.links import stable_paths_report

if TYPE_CHECKING:
    from pathlib import Path


def docs_quality_report(root: Path) -> dict[str, object]:
    """Report composite documentation quality across registry, links, glossary, and examples."""
    health = docs_health_report(root)
    link_integrity = link_integrity_report(root)
    glossary = glossary_report(root)
    invalid_state = string_list(health.get("invalid_state"))
    duplicate_subjects = string_list(health.get("duplicate_subjects"))
    missing_visible_sections = string_list(health.get("missing_visible_sections"))
    checks = {
        "taxonomy": {
            "ok": not invalid_state and not duplicate_subjects,
            "required_gaps": invalid_state + duplicate_subjects,
        },
        "visible_structure": {
            "ok": not missing_visible_sections,
            "required_gaps": missing_visible_sections,
        },
        "stable_paths": stable_paths_report(root),
        "link_integrity": link_integrity,
        "glossary": glossary,
    }
    command_examples = command_examples_report(root)
    required_gaps = [
        gap for check in checks.values() for gap in string_list(check.get("required_gaps"))
    ] + string_list(command_examples.get("required_gaps"))
    return {
        "ok": not required_gaps and health.get("ok") is True and command_examples.get("ok") is True,
        "style_goals": ["faithful", "expressive", "elegant"],
        "required_gaps": required_gaps,
        "checks": checks,
        "health": health,
        "command_examples": command_examples,
    }
