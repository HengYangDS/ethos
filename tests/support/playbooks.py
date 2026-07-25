from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.assistants.skills.packages import compute_skill_package_digest

if TYPE_CHECKING:
    from pathlib import Path

OFFICIAL_PLAYBOOK_SKILL = """---
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


def write_v2_playbook_package(skills_root: Path, skill_id: str) -> str:
    package_dir = skills_root / skill_id
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(
        OFFICIAL_PLAYBOOK_SKILL.replace("name: sample-skill", f"name: {skill_id}"), encoding="utf-8"
    )
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    package_manifest = package_dir / "package.toml"
    package_manifest.write_text(
        f"""
schema_version = 2
id = "{skill_id}"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[quality]
placeholder_allowed = false

[[capability]]
id = "ethos.status"
kind = "command_readonly"
command = ["ethos", "status", "--json"]
""".lstrip(),
        encoding="utf-8",
    )
    return package_manifest.as_posix()
