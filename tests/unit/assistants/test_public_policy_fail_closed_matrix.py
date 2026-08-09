from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import pytest

from ethos.assistants.playbooks import playbooks_report
from ethos.assistants.skills.capabilities import capability_records
from ethos.assistants.skills.capabilities import contained_package_path
from ethos.assistants.skills.packages import compute_skill_package_digest
from ethos.assistants.skills.packages import validate_skill_markdown
from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import portfolio_coverage
from ethos.assistants.skills.portfolio import portfolio_design
from ethos.assistants.skills.portfolio import portfolio_retirement

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _skill_text(*, name: str = "sample", description: str = "Use when testing.") -> str:
    return f"""---
name: {name}
description: {description}
---

# Sample

## When to Use

Use this skill for governed testing.

## Workflow

1. Read repository truth.

## Evidence

Keep exact evidence.

## Trust Boundary

Repository source and evidence are truth.
"""


def _package(root: Path, skill_id: str = "sample") -> tuple[Path, Path]:
    package_dir = root / ".agents/skills" / skill_id
    skill = package_dir / "SKILL.md"
    _write(skill, _skill_text(name=skill_id))
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    manifest = package_dir / "package.toml"
    _write(
        manifest,
        f"""schema_version = 2
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
""",
    )
    return package_dir, manifest


def test_capability_policy_rejects_mutation_untrusted_scripts_and_fake_proof(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / "skill"
    _write(package_dir / "check.py", "print('ok')\n")
    capabilities: list[dict[str, Any]] = [
        {"id": "readonly-mutation", "kind": "command_readonly", "command": ["ethos", "land"]},
        {"id": "readonly-unknown", "kind": "command_readonly", "command": ["unknown"]},
        {"id": "script-mutation", "kind": "script_readonly", "command": ["ethos", "land"]},
        {"id": "script-empty", "kind": "script_readonly", "command": []},
        {"id": "script-option", "kind": "script_readonly", "command": ["-unsafe"]},
        {"id": "script-interpreter", "kind": "script_readonly", "command": ["python3"]},
        {"id": "script-unlisted", "kind": "script_readonly", "command": ["check.py"]},
        {"id": "proof-fake", "kind": "command_proof", "command": ["ethos", "status"]},
    ]
    gaps, records = capability_records(
        "sample",
        capabilities,
        package_dir=package_dir,
        included_files=frozenset(),
    )
    assert gaps == [
        "skill_package_capability_readonly_mutating:sample:readonly-mutation",
        "skill_package_capability_readonly_untrusted:sample:readonly-unknown",
        "skill_package_capability_readonly_mutating:sample:script-mutation",
        "skill_package_capability_readonly_untrusted:sample:script-empty",
        "skill_package_capability_readonly_untrusted:sample:script-option",
        "skill_package_capability_readonly_untrusted:sample:script-interpreter",
        "skill_package_capability_readonly_untrusted:sample:script-unlisted",
        "skill_package_capability_proof_invalid:sample:proof-fake",
    ]
    assert [record["id"] for record in records] == [item["id"] for item in capabilities]
    assert not contained_package_path(package_dir, "/absolute")
    assert not contained_package_path(package_dir, "../escape")


def test_manifest_public_report_blocks_escape_missing_invalid_and_stale_digest(
    tmp_path: Path,
) -> None:
    escaped = validate_skill_package_manifest(tmp_path, "../outside/package.toml")
    missing = validate_skill_package_manifest(tmp_path, ".agents/skills/missing/package.toml")
    invalid_path = tmp_path / ".agents/skills/invalid/package.toml"
    _write(invalid_path, "schema_version = [\n")
    invalid = validate_skill_package_manifest(
        tmp_path, invalid_path.relative_to(tmp_path).as_posix()
    )
    assert escaped["required_gaps"] == ["skill_package_manifest_path_escape:outside"]
    assert missing["required_gaps"] == ["skill_package_manifest_missing:missing"]
    assert invalid["required_gaps"] == ["skill_package_manifest_invalid_toml:invalid"]

    _, manifest = _package(tmp_path, "stale")
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            'expected_digest = "sha256:', 'expected_digest = "sha256:0'
        ),
        encoding="utf-8",
    )
    stale = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())
    assert "skill_package_expected_digest_invalid:stale" in stale["required_gaps"]


def test_manifest_and_markdown_reports_preserve_content_quality_failures(tmp_path: Path) -> None:
    package_dir, manifest = _package(tmp_path, "quality")
    skill = package_dir / "SKILL.md"
    description = "Not a trigger " + "word " * 65
    workflow = "\n".join(f"{index}. step" for index in range(10))
    padding = "\n".join("content" for _ in range(170))
    _write(
        skill,
        f"""---
name: wrong-name
description: {description}
---
## When to Use
TBD
## Workflow
{workflow}
## Evidence
placeholder
## Trust Boundary
coming soon
{padding}
""",
    )
    report = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())
    expected = {
        "skill_package_digest_mismatch:quality",
        "skill_quality_name_mismatch:quality:wrong-name",
        "skill_quality_description_not_trigger:quality",
        "skill_quality_description_too_long:quality",
        "skill_quality_entrypoint_too_long:quality:191",
        "skill_quality_workflow_too_many_steps:quality:10",
        "skill_quality_progressive_disclosure_missing:quality",
        "skill_quality_missing_truth_boundary:quality",
        "skill_quality_placeholder_section:quality:When to Use",
        "skill_quality_placeholder_section:quality:Evidence",
    }
    assert report["verdict"] == "block"
    assert expected <= set(report["required_gaps"])

    missing = validate_skill_markdown(tmp_path, "absent.md", "absent")
    malformed = tmp_path / "malformed.md"
    _write(malformed, "---\nname: malformed\n")
    malformed_report = validate_skill_markdown(tmp_path, malformed.name, "malformed")
    assert missing["required_gaps"] == ["skill_missing_file:absent"]
    assert "skill_quality_missing_frontmatter:malformed" in malformed_report["required_gaps"]


def _record(skill_id: str, **updates: object) -> dict[str, object]:
    return {
        "id": skill_id,
        "authority": "primary",
        "lifecycle": "active",
        "primary_subject": "subject",
        "subjects": ["subject"],
        "path_globs": ["src/**"],
        "intent_tokens": ["govern"],
        "operation": "plan",
        **updates,
    }


def test_portfolio_reports_duplicate_overloaded_and_unowned_routes(tmp_path: Path) -> None:
    coverage = portfolio_coverage(
        {
            "required_primary_subjects": ["subject", "missing"],
            "single_owner_subjects": ["subject"],
        },
        [
            _record("first"),
            _record("second"),
            _record("inactive", lifecycle="retired"),
            _record("empty", primary_subject=""),
        ],
    )
    assert coverage["required_gaps"] == [
        "skill_portfolio_subject_missing:missing",
        "skill_portfolio_subject_duplicate:subject:first,second",
    ]

    records = [
        _record(
            skill_id,
            primary_subject="unrouted" if skill_id == "first" else "subject",
            path_globs=["shared/**"],
            intent_tokens=["shared-token"],
        )
        for skill_id in ("first", "second", "third")
    ]
    packages = [{"id": "first", "files": [str(index) for index in range(7)]}]
    design = portfolio_design(records, packages)
    assert {
        "skill_portfolio_primary_subject_not_routed:first",
        "skill_portfolio_package_overloaded:first:7",
        "skill_portfolio_path_glob_duplicate:shared/**:first,second,third",
        "skill_portfolio_intent_token_overclaimed:shared-token:first,second,third",
        "skill_portfolio_route_duplicate:subject:plan:second,third",
    } <= set(design["required_gaps"])

    live = tmp_path / ".agents/skills/live"
    live.mkdir(parents=True)
    retirement = portfolio_retirement(
        {
            "retired": {
                "active": {},
                "invalid": "not-a-record",
                "live": {
                    "reason": "replaced",
                    "retired_on": "2026-08-10",
                    "kill_signal": "replacement proven",
                    "path": ".agents/skills/live",
                },
            }
        },
        [_record("active")],
        tmp_path,
    )
    assert retirement["required_gaps"] == [
        "skill_retirement_active_duplicate:active",
        "skill_retirement_invalid:invalid",
        "skill_retirement_live_path:live:.agents/skills/live",
    ]


def test_playbooks_public_report_rejects_unknown_mode_and_malformed_activation(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="unsupported playbook mode"):
        playbooks_report(tmp_path, mode="legacy")

    activation = tmp_path / ".agents/skills/activation.toml"
    _write(activation, "[meta\n")
    report = playbooks_report(tmp_path)
    assert report["verdict"] == "block"
    assert ".agents/skills/activation.toml:invalid_toml" in report["required_gaps"]
    assert ".agents/skills/README.md" in report["required_gaps"]
