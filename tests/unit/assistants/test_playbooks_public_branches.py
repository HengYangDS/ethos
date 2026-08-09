# ruff: noqa: SLF001
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import ethos.assistants.playbooks as playbooks
from ethos.assistants.skills.packages import compute_skill_package_digest

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _record(**updates: object) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": "sample",
        "path": ".agents/skills/sample/SKILL.md",
        "package_manifest": ".agents/skills/sample/package.toml",
        "primary_subject": "governance",
        "operation": "govern",
        "authority": "primary",
        "lifecycle": "active",
        "route_subjects": ["governance"],
        "activation": {"path_globs": ["src/**"]},
        "routing": {"intent_tokens": ["govern"]},
        "obligations": {"pre_reads": ["AGENTS.md"], "post_checks": ["ethos status --json"]},
        "relations": {"requires": [], "excludes": []},
        "boundary": "repository-truth",
    }
    record.update(updates)
    return record


def _package(root: Path) -> dict[str, Any]:
    package = root / ".agents/skills/sample"
    skill = package / "SKILL.md"
    _write(
        skill,
        """---
name: sample
description: Use when testing the public playbook contract.
---

# Sample

## When to Use

Use this skill for public behavior tests.

## Workflow

1. Read repository truth.

## Evidence

Run `ethos status --json`.

## Trust Boundary

Repository source and command JSON are truth.
""",
    )
    digest = compute_skill_package_digest(package, ["SKILL.md"])
    _write(
        package / "package.toml",
        f"""schema_version = 2
id = "sample"
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
""",
    )
    return {
        "id": "sample",
        "entrypoint": "SKILL.md",
        "manifest": ".agents/skills/sample/package.toml",
        "capabilities": [{"command": ["ethos", "status", "--json"]}],
        "required_gaps": [],
    }


def test_collect_playbook_records_preserves_identity_path_and_command_gaps(
    monkeypatch, tmp_path: Path
) -> None:
    report = _package(tmp_path)
    reports = iter((report, report, report, report))
    monkeypatch.setattr(playbooks, "validate_skill_package_manifest", lambda *_a: next(reports))
    monkeypatch.setattr(
        playbooks,
        "validate_skill_markdown",
        lambda *_a: {"required_gaps": ["skill_quality_gap"]},
    )
    monkeypatch.setattr(playbooks, "capability_command_strings", lambda _caps: [])
    missing = _record(id="")
    escaped = _record(id="escaped", path="../escaped/SKILL.md")
    absent = _record(id="absent", path=".agents/skills/absent/SKILL.md")
    quality = _record()

    result = playbooks._collect_playbook_records(
        tmp_path,
        registry={"records": [missing, escaped, absent, quality]},
    )

    assert result["required_gaps"] == ["skill_missing_id", "skill_missing_file:absent"]
    assert {
        "playbook_skill_path_escape:escaped",
        "skill_quality_gap",
        "playbook_skill_missing_commands:escaped",
        "playbook_skill_missing_commands:absent",
        "playbook_skill_missing_commands:sample",
    } <= set(result["v2_gaps"])
    assert [record["id"] for record in result["records"]] == ["escaped", "absent", "sample"]


def test_playbook_record_helpers_fail_closed_for_incomplete_and_escaped_records(
    tmp_path: Path,
) -> None:
    incomplete = _record(
        primary_subject="",
        operation="",
        authority="",
        lifecycle="",
        activation={"path_globs": []},
        obligations={"pre_reads": [], "post_checks": []},
        package_manifest="",
    )
    assert playbooks._strict_record_gaps(incomplete) == [
        "playbook_skill_missing_subject:sample",
        "playbook_skill_missing_operation:sample",
        "playbook_skill_missing_authority:sample",
        "playbook_skill_missing_lifecycle:sample",
        "playbook_skill_missing_path_globs:sample",
        "playbook_skill_missing_pre_reads:sample",
        "playbook_skill_missing_post_checks:sample",
        "skill_package_manifest_missing:sample",
    ]
    assert playbooks._manifest_path(incomplete) == ".agents/skills/sample/package.toml"
    assert playbooks._record_path_gaps(tmp_path, "sample", "../outside/SKILL.md") == [
        "playbook_skill_path_escape:sample"
    ]
    assert playbooks._root_relative(tmp_path, "/absolute") == ""
    assert playbooks._root_relative(tmp_path, "../outside") == ""


def test_package_entrypoint_binding_handles_missing_escape_and_mismatch(tmp_path: Path) -> None:
    assert playbooks._package_entrypoint_gaps(tmp_path, "sample", "SKILL.md", {}) == []
    assert (
        playbooks._package_entrypoint_gaps(
            tmp_path,
            "sample",
            "../outside/SKILL.md",
            {"manifest": ".agents/skills/sample/package.toml", "entrypoint": "SKILL.md"},
        )
        == []
    )
    assert playbooks._package_entrypoint_gaps(
        tmp_path,
        "sample",
        ".agents/skills/sample/OTHER.md",
        {"manifest": ".agents/skills/sample/package.toml", "entrypoint": "SKILL.md"},
    ) == ["skill_package_entrypoint_mismatch:sample"]
