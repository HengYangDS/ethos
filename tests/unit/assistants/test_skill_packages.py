from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.assistants.skills.packages import compute_skill_package_digest
from ethos.assistants.skills.packages import validate_skill_package_manifest

if TYPE_CHECKING:
    from pathlib import Path

OFFICIAL_SKILL = """---
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

Run `ethos report --json` and keep the output with the delivery note.

## Trust Boundary

Repository source, tests, schemas, docs, claims, evidence, and command JSON are truth.
"""


def _write_manifest(package_dir: Path, expected_digest: str) -> Path:
    path = package_dir / "package.toml"
    path.write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{expected_digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "ethos.report"
kind = "command_readonly"
command = ["ethos", "report", "--json"]
""".lstrip(),
        encoding="utf-8",
    )
    return path


def test_skill_package_manifest_binds_entrypoint_digest(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    manifest = _write_manifest(package_dir, digest)

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["ok"] is True
    assert result["digest"] == digest
    assert result["required_gaps"] == []
    assert result["capabilities"] == [
        {
            "id": "ethos.report",
            "kind": "command_readonly",
            "command": ["ethos", "report", "--json"],
        }
    ]


def test_skill_package_manifest_rejects_stale_digest(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    manifest = _write_manifest(package_dir, "sha256:" + ("0" * 64))

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["ok"] is False
    assert "skill_package_digest_mismatch:sample-skill" in result["required_gaps"]


def test_skill_package_manifest_reports_missing_include_without_crashing(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    (package_dir / "package.toml").write_text(
        """
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md", "MISSING.md"]
expected_digest = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert "skill_package_file_missing:sample-skill:MISSING.md" in result["required_gaps"]


def test_skill_package_manifest_rejects_path_escape(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    (package_dir / "package.toml").write_text(
        """
schema_version = 2
id = "sample-skill"
entrypoint = "../other/SKILL.md"
digest_algorithm = "sha256"
include = ["../other/SKILL.md"]
expected_digest = "sha256:0000"
required_sections = ["When to Use"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert "skill_package_path_escape:sample-skill:../other/SKILL.md" in result["required_gaps"]


def test_skill_package_manifest_rejects_escaped_manifest_path(tmp_path: Path) -> None:
    result = validate_skill_package_manifest(tmp_path, "../outside/package.toml")

    assert result["ok"] is False
    assert "skill_package_manifest_path_escape:outside" in result["required_gaps"]


def test_skill_package_manifest_requires_schema_fields(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    (package_dir / "package.toml").write_text(
        """
id = "sample-skill"
entrypoint = "SKILL.md"
include = ["SKILL.md"]
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert "skill_package_schema_version_invalid:sample-skill" in result["required_gaps"]
    assert "skill_package_digest_algorithm_invalid:sample-skill" in result["required_gaps"]
    assert "skill_package_expected_digest_missing:sample-skill" in result["required_gaps"]


def test_skill_package_manifest_rejects_placeholder_sections_when_disallowed(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(
        """---
name: sample-skill
description: Use when governing sample repositories with ETHOS.
---

# Sample Skill

## When to Use

TBD

## Workflow

TBD

## Evidence

TBD

## Trust Boundary

Repository source, tests, schemas, docs, claims, evidence, and command JSON are truth.
""",
        encoding="utf-8",
    )
    (package_dir / "package.toml").write_text(
        """
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[quality]
placeholder_allowed = false
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert "skill_quality_placeholder_section:sample-skill:When to Use" in result["required_gaps"]


def test_skill_package_manifest_validates_capability_semantics(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "ethos.land"
kind = "command_readonly"
command = ["ethos", "land", "--apply"]

[[capability]]
id = "ethos.status"
kind = "command_mutation_guarded"
command = ["ethos", "status", "--json"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert (
        "skill_package_capability_readonly_mutating:sample-skill:ethos.land"
        in result["required_gaps"]
    )
    assert (
        "skill_package_capability_guard_missing:sample-skill:ethos.status"
        in result["required_gaps"]
    )


def test_skill_package_manifest_rejects_untrusted_readonly_capabilities(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "shell.delete"
kind = "command_readonly"
command = ["rm", "-rf", "tmp"]

[[capability]]
id = "script.inspect"
kind = "script_readonly"
command = ["scripts/inspect.sh"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert (
        "skill_package_capability_readonly_untrusted:sample-skill:shell.delete"
        in result["required_gaps"]
    )
    assert (
        "skill_package_capability_readonly_untrusted:sample-skill:script.inspect"
        in result["required_gaps"]
    )


def test_skill_package_manifest_rejects_non_proof_internal_commands(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "ethos.internal-canonize"
kind = "command_proof"
command = ["ethos", "internal", "canonize"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert (
        "skill_package_capability_proof_invalid:sample-skill:ethos.internal-canonize"
        in result["required_gaps"]
    )


def test_skill_markdown_rejects_non_trigger_description(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(
        OFFICIAL_SKILL.replace(
            "description: Use when governing sample repositories with ETHOS.",
            "description: Governs sample repositories with ETHOS.",
        ),
        encoding="utf-8",
    )
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    manifest = _write_manifest(package_dir, digest)

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["ok"] is False
    assert "skill_quality_description_not_trigger:sample-skill" in result["required_gaps"]


def test_skill_markdown_rejects_overlong_entrypoint_without_progressive_disclosure(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    long_body = "\n".join(f"Extra line {index}." for index in range(100))
    (package_dir / "SKILL.md").write_text(
        OFFICIAL_SKILL.replace("## Evidence", f"{long_body}\n\n## Evidence"),
        encoding="utf-8",
    )
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    manifest = _write_manifest(package_dir, digest)

    result = validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())

    assert result["ok"] is False
    assert "skill_quality_progressive_disclosure_missing:sample-skill" in result["required_gaps"]


def test_skill_package_manifest_accepts_readonly_repo_local_script(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    scripts_dir = package_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "audit.py").write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md", "scripts/audit.py"])
    (package_dir / "package.toml").write_text(
        f'''
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md", "scripts/audit.py"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "sample.audit"
kind = "script_readonly"
command = ["scripts/audit.py", "."]
'''.lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is True
    assert result["required_gaps"] == []
    assert result["capabilities"] == [
        {
            "id": "sample.audit",
            "kind": "script_readonly",
            "command": ["scripts/audit.py", "."],
        }
    ]


def test_skill_package_manifest_rejects_untrusted_readonly_script(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f'''
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[[capability]]
id = "sample.escape"
kind = "script_readonly"
command = ["../outside.sh"]

[[capability]]
id = "sample.mutating"
kind = "script_readonly"
command = ["scripts/audit.py", "--apply"]
'''.lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(
        tmp_path,
        ".agents/skills/sample-skill/package.toml",
    )

    assert result["ok"] is False
    assert (
        "skill_package_capability_readonly_untrusted:sample-skill:sample.escape"
        in result["required_gaps"]
    )
    assert (
        "skill_package_capability_readonly_mutating:sample-skill:sample.mutating"
        in result["required_gaps"]
    )


def test_skill_package_manifest_accepts_eval_metadata(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[eval]
treatment_id = "runtime-v1"
metrics = ["pass_at_k", "instability_gap"]
pass_at_k = 0.8
instability_gap = 0.1
evidence_refs = ["evidence/chronicle/sample/2026-07-09.md"]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(tmp_path, ".agents/skills/sample-skill/package.toml")

    assert result["ok"] is True
    assert result["eval"]["truth_boundary"] == "skill_metadata_only"
    assert result["eval"]["metrics"] == ["pass_at_k", "instability_gap"]


def test_skill_package_manifest_rejects_invalid_eval_metadata(tmp_path: Path) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[eval]
metrics = ["bad_metric"]
pass_at_k = 1.5
evidence_refs = []
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_skill_package_manifest(tmp_path, ".agents/skills/sample-skill/package.toml")

    assert result["ok"] is False
    assert "skill_package_eval_treatment_missing:sample-skill" in result["required_gaps"]
    assert "skill_package_eval_metric_unknown:sample-skill:bad_metric" in result["required_gaps"]
    assert (
        "skill_package_eval_metric_out_of_bounds:sample-skill:pass_at_k" in result["required_gaps"]
    )
    assert "skill_package_eval_evidence_refs_missing:sample-skill" in result["required_gaps"]


def test_skill_package_manifest_rejects_non_table_and_empty_eval_metadata(
    tmp_path: Path,
) -> None:
    package_dir = tmp_path / ".agents" / "skills" / "sample-skill"
    package_dir.mkdir(parents=True)
    (package_dir / "SKILL.md").write_text(OFFICIAL_SKILL, encoding="utf-8")
    digest = compute_skill_package_digest(package_dir, ["SKILL.md"])
    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]
eval = "not-a-table"
""".lstrip(),
        encoding="utf-8",
    )

    non_table = validate_skill_package_manifest(
        tmp_path, ".agents/skills/sample-skill/package.toml"
    )

    assert non_table["ok"] is False
    assert "skill_package_eval_invalid:sample-skill" in non_table["required_gaps"]

    (package_dir / "package.toml").write_text(
        f"""
schema_version = 2
id = "sample-skill"
entrypoint = "SKILL.md"
digest_algorithm = "sha256"
include = ["SKILL.md"]
expected_digest = "{digest}"
required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]

[eval]
treatment_id = "runtime-v1"
evidence_refs = ["evidence/chronicle/sample/2026-07-09.md"]
""".lstrip(),
        encoding="utf-8",
    )

    missing_metrics = validate_skill_package_manifest(
        tmp_path, ".agents/skills/sample-skill/package.toml"
    )

    assert missing_metrics["ok"] is False
    assert "skill_package_eval_metrics_missing:sample-skill" in missing_metrics["required_gaps"]
