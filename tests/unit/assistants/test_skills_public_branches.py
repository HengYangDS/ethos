from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.assistants.skills.packages import compute_skill_package_digest
from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import skill_portfolio_report

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
        f'path = "{path or f".agents/skills/{skill_id}/SKILL.md"}"\n'
        f"{f'package_manifest = {package_manifest!r}\n' if package_manifest else ''}"
        f"{fields}"
    ).replace("'", '"')


def test_skill_portfolio_report_preserves_identity_path_quality_and_command_gaps(
    tmp_path: Path,
) -> None:
    skills = tmp_path / ".agents/skills"
    _write(skills / "README.md", "# Skills\n")
    for skill_id in (
        "escaped",
        "absolute",
        "absent",
        "quality",
        "mismatch",
    ):
        _package(tmp_path, skill_id)
    _write(skills / "mismatch/OTHER.md", "alternate entrypoint\n")
    _write(skills / "quality/SKILL.md", "# malformed\n")
    activation = (
        '[meta]\nversion = 2\nsource_of_truth = "repository"\n\n'
        "[coverage]\nrequired_primary_subjects = []\nsingle_owner_subjects = []\n\n"
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
        + _record(
            "mismatch",
            path=".agents/skills/mismatch/OTHER.md",
            package_manifest=".agents/skills/mismatch/package.toml",
        )
    )
    _write(skills / "activation.toml", activation)

    report = skill_portfolio_report(tmp_path)
    gaps = set(report["required_gaps"])

    assert "digest" not in report["registry"]
    assert report["verdict"] == "block"
    assert "skill_missing_file:absent" in gaps
    assert {
        "skill_path_escape:escaped",
        "skill_path_escape:absolute",
        "skill_quality_missing_frontmatter:quality",
        "skill_missing_commands:escaped",
        "skill_missing_commands:absent",
        "skill_missing_commands:quality",
        "skill_package_entrypoint_mismatch:mismatch",
    } <= gaps
    assert report["skills"] == [
        "escaped",
        "absolute",
        "absent",
        "quality",
        "mismatch",
    ]
    records = {record["id"]: record for record in report["records"]}
    assert records["mismatch"]["commands"] == []


def test_skill_portfolio_report_rejects_missing_invalid_and_unsupported_activation(
    tmp_path: Path,
) -> None:
    missing = skill_portfolio_report(tmp_path)
    assert missing["verdict"] == "block"
    assert ".agents/skills/activation.toml" in missing["required_gaps"]
    assert ".agents/skills" in missing["required_gaps"]

    _write(tmp_path / ".agents/skills/activation.toml", "[meta\n")
    invalid = skill_portfolio_report(tmp_path)
    assert ".agents/skills/activation.toml:invalid_toml" in invalid["required_gaps"]


def test_skill_report_has_no_generation_mode_or_duplicate_score(tmp_path: Path) -> None:
    """Current skill obligations have one verdict, not a single-mode compatibility plane."""
    report = skill_portfolio_report(tmp_path)
    assert "mode" not in report
    assert "v2_compliance" not in report


@pytest.mark.parametrize("extra", ["", 'name = "discarded"', 'unexpected = "discarded"'])
def test_original_activation_fields_cannot_disappear(tmp_path: Path, extra: str) -> None:
    """Validation precedes normalization that would otherwise erase unknown input."""
    _package(tmp_path, "valid", commands=True)
    skills = tmp_path / ".agents/skills"
    _write(skills / "README.md", "# Skills\n")
    activation = (
        '[meta]\nversion = 2\nsource_of_truth = "repository"\n'
        "[coverage]\nrequired_primary_subjects = []\nsingle_owner_subjects = []\n"
        + _record("valid", package_manifest=".agents/skills/valid/package.toml")
        + extra
        + "\n"
    )
    _write(skills / "activation.toml", activation)

    report = skill_portfolio_report(tmp_path)

    assert report["verdict"] == ("block" if extra else "pass")
    assert bool(report["required_gaps"]) is bool(extra)
    if extra:
        assert any("activation" in gap and "invalid" in gap for gap in report["required_gaps"])


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "subject",
        "operation",
        "authority",
        "lifecycle",
        "path_globs",
        "pre_reads",
        "post_checks",
        "package_manifest",
    ],
)
def test_incomplete_original_skill_is_rejected(tmp_path: Path, field: str) -> None:
    """Every former record obligation is enforced before lossy projection."""
    record = _record("sample", package_manifest=".agents/skills/sample/package.toml")
    record = "\n".join(line for line in record.splitlines() if not line.startswith(f"{field} ="))
    _write(
        tmp_path / ".agents/skills/activation.toml",
        '[meta]\nversion = 2\nsource_of_truth = "repository"\n'
        "[coverage]\nrequired_primary_subjects = []\nsingle_owner_subjects = []\n" + record,
    )
    report = skill_portfolio_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["records"] == []
    assert any(field in gap for gap in report["required_gaps"])


def test_skill_schema_cannot_be_replaced_by_adopter_checkout(tmp_path: Path) -> None:
    """Adopter payloads cannot replace the schema that interprets their package."""
    _package(tmp_path, "valid", commands=True)
    manifest = ".agents/skills/valid/package.toml"
    expected = validate_skill_package_manifest(tmp_path, manifest)
    assert expected["verdict"] == "pass"
    _write(tmp_path / "system/schemas/kernel/skill-package-manifest.schema.json", "false\n")
    assert validate_skill_package_manifest(tmp_path, manifest) == expected
