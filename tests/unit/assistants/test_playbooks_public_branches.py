from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.assistants.playbooks import playbooks_report
from ethos.assistants.skills.packages import compute_skill_package_digest

if TYPE_CHECKING:
    from pathlib import Path


_SKILL = """---
name: {skill_id}
description: Use when testing the public playbook contract.
---

# {skill_id}

## When to Use

Use this skill for public behavior tests.

## Workflow

1. Read repository truth.

## Evidence

Run `ethos status --json`.

## Trust Boundary

Repository source and command JSON are truth.
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _package(root: Path, skill_id: str, *, commands: bool = False) -> None:
    package = root / f".agents/skills/{skill_id}"
    skill = package / "SKILL.md"
    _write(skill, _SKILL.format(skill_id=skill_id))
    digest = compute_skill_package_digest(package, ["SKILL.md"])
    capability = (
        '\n[[capability]]\nid = "ethos.status"\nkind = "command_readonly"\n'
        'command = ["ethos", "status", "--json"]\n'
        if commands
        else ""
    )
    _write(
        package / "package.toml",
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
    )


def _record(
    skill_id: str,
    *,
    path: str = "",
    package_manifest: str = "",
    complete: bool = True,
) -> str:
    fields = (
        'subject = "governance"\noperation = "govern"\nauthority = "primary"\n'
        'lifecycle = "active"\npath_globs = ["src/**"]\nsubjects = ["governance"]\n'
        'intent_tokens = ["govern"]\npre_reads = ["AGENTS.md"]\n'
        'post_checks = ["ethos status --json"]\nboundary = "repository-truth"\n'
        if complete
        else ""
    )
    return (
        "[[skill]]\n"
        f'id = "{skill_id}"\n'
        f"{f'path = {path!r}\n' if path else ''}"
        f"{f'package_manifest = {package_manifest!r}\n' if package_manifest else ''}"
        f"{fields}"
    ).replace("'", '"')


def test_playbooks_report_preserves_identity_path_quality_and_command_gaps(tmp_path: Path) -> None:
    skills = tmp_path / ".agents/skills"
    _write(skills / "README.md", "# Skills\n")
    for skill_id in (
        "escaped",
        "absolute",
        "absent",
        "quality",
        "incomplete",
        "mismatch",
    ):
        _package(tmp_path, skill_id)
    _write(skills / "mismatch/OTHER.md", "alternate entrypoint\n")
    _write(skills / "quality/SKILL.md", "# malformed\n")
    activation = (
        '[meta]\nversion = 2\nsource_of_truth = "repository"\n\n'
        "[coverage]\nrequired_primary_subjects = []\nsingle_owner_subjects = []\n\n"
        + _record("")
        + _record(
            "escaped",
            path="../escaped/SKILL.md",
            package_manifest=".agents/skills/escaped/package.toml",
        )
        + _record(
            "absolute",
            path="/outside/SKILL.md",
            package_manifest=".agents/skills/absolute/package.toml",
        )
        + _record(
            "absent",
            path=".agents/skills/not-present/SKILL.md",
            package_manifest=".agents/skills/absent/package.toml",
        )
        + _record("quality", package_manifest=".agents/skills/quality/package.toml")
        + _record("incomplete", complete=False)
        + _record(
            "mismatch",
            path=".agents/skills/mismatch/OTHER.md",
            package_manifest=".agents/skills/mismatch/package.toml",
        )
    )
    _write(skills / "activation.toml", activation)

    report = playbooks_report(tmp_path)
    gaps = set(report["required_gaps"])

    assert report["verdict"] == "block"
    assert {"skill_missing_id", "skill_missing_file:absent"} <= gaps
    assert {
        "playbook_skill_path_escape:escaped",
        "playbook_skill_path_escape:absolute",
        "skill_quality_missing_frontmatter:quality",
        "playbook_skill_missing_commands:escaped",
        "playbook_skill_missing_commands:absent",
        "playbook_skill_missing_commands:quality",
        "playbook_skill_missing_subject:incomplete",
        "playbook_skill_missing_operation:incomplete",
        "playbook_skill_missing_authority:incomplete",
        "playbook_skill_missing_path_globs:incomplete",
        "playbook_skill_missing_pre_reads:incomplete",
        "playbook_skill_missing_post_checks:incomplete",
        "skill_package_manifest_missing:incomplete",
        "skill_package_entrypoint_mismatch:mismatch",
    } <= gaps
    assert report["skills"] == [
        "escaped",
        "absolute",
        "absent",
        "quality",
        "incomplete",
        "mismatch",
    ]
    records = {record["id"]: record for record in report["records"]}
    assert records["incomplete"]["package_manifest"] == (".agents/skills/incomplete/package.toml")
    assert records["mismatch"]["commands"] == []


def test_playbooks_report_rejects_missing_invalid_and_unsupported_activation(
    tmp_path: Path,
) -> None:
    missing = playbooks_report(tmp_path)
    assert missing["verdict"] == "block"
    assert ".agents/skills/activation.toml" in missing["required_gaps"]
    assert ".agents/skills" in missing["required_gaps"]

    _write(tmp_path / ".agents/skills/activation.toml", "[meta\n")
    invalid = playbooks_report(tmp_path)
    assert ".agents/skills/activation.toml:invalid_toml" in invalid["required_gaps"]

    with pytest.raises(ValueError, match="unsupported playbook mode: legacy"):
        playbooks_report(tmp_path, mode="legacy")
