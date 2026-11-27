"""Construct skill-package fixtures with their declared capability metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.assistants.skills.packages import compute_skill_package_digest

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_SKILL = """---
name: sample-skill
description: Use when governing sample repositories with ETHOS.
---

# Sample Skill

## When to Use

Use this skill for sample governance work.

## Workflow

1. Read the repository guidance.
2. Run the focused ETHOS check.
3. Record evidence before making a claim.

## Evidence

Run `ethos status --json` and keep the output with the delivery note.

## Trust Boundary

Repository source, tests, schemas, docs, claims, evidence, and command JSON are truth.
"""


def write_skill_package(
    skills_root: Path, skill_id: str, *, text: str = SAMPLE_SKILL, commands: bool = True
) -> Path:
    """Write one digest-bound skill package, optionally with its read-only command capability.

    Return the path of its ``package.toml``.
    """
    package_dir = skills_root / skill_id
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(
        text.replace("name: sample-skill", f"name: {skill_id}"), encoding="utf-8"
    )
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    capability = (
        '\n[[capability]]\nid = "ethos.status"\nkind = "command_readonly"\n'
        'command = ["ethos", "status", "--json"]\n'
        if commands
        else ""
    )
    package_manifest = package_dir / "package.toml"
    package_manifest.write_text(
        f"""schema_version = 2
id = "{skill_id}"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[quality]
placeholder_allowed = false
{capability}""",
        encoding="utf-8",
    )
    return package_manifest
