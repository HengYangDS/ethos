# ruff: noqa: TC003, FLY002
from __future__ import annotations

from pathlib import Path

from ethos.assistants import skill_packages as sp

SKILL_MD = """---
name: sample
description: sample skill
---

# Sample

## When to Use
Use when repository truth matters.

## Workflow
Run ethos status.

## Evidence
Command JSON is evidence.

## Trust Boundary
Repository truth is the source of truth.
"""


def write_skill(root: Path, manifest_extra: str = "", skill_text: str = SKILL_MD) -> Path:
    package = root / ".agents" / "skills" / "sample"
    package.mkdir(parents=True)
    (package / "SKILL.md").write_text(skill_text, encoding="utf-8")
    digest = sp.compute_skill_package_digest(package, ["SKILL.md"])
    (package / "skill-package.toml").write_text(
        "\n".join(
            [
                'id = "sample"',
                "schema_version = 2",
                'digest_algorithm = "sha256"',
                'entrypoint = "SKILL.md"',
                'include = ["SKILL.md"]',
                f'expected_digest = "{digest}"',
                'required_sections = ["When to Use", "Workflow", "Evidence", "Trust Boundary"]',
                manifest_extra,
            ]
        ),
        encoding="utf-8",
    )
    return package / "skill-package.toml"


def test_skill_package_validates_manifest_digest_markdown_and_capabilities(tmp_path: Path) -> None:
    manifest = write_skill(
        tmp_path,
        "\n".join(
            [
                "[[capability]]",
                'id = "status"',
                'kind = "command_readonly"',
                'command = ["ethos", "status", "--json"]',
                "[[capability]]",
                'id = "prove"',
                'kind = "command_proof"',
                'command = ["ethos", "prove", "--json"]',
                "[[capability]]",
                'id = "land"',
                'kind = "command_mutation_guarded"',
                'command = ["ethos", "land", "--apply"]',
                'guard = "prewrite"',
            ]
        ),
    )
    report = sp.validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())
    assert report["ok"] is True
    assert len(report["capabilities"]) == 3


def test_skill_package_manifest_and_markdown_rejections(tmp_path: Path) -> None:
    assert (
        "skill_package_manifest_path_escape:.."
        in sp.validate_skill_package_manifest(tmp_path, "../skill-package.toml")["required_gaps"]
    )
    assert (
        "skill_package_manifest_missing:missing"
        in sp.validate_skill_package_manifest(
            tmp_path, ".agents/skills/missing/skill-package.toml"
        )["required_gaps"]
    )
    package = tmp_path / ".agents" / "skills" / "bad"
    package.mkdir(parents=True)
    (package / "skill-package.toml").write_text("[[bad]\n", encoding="utf-8")
    assert (
        "skill_package_manifest_invalid_toml:bad"
        in sp.validate_skill_package_manifest(tmp_path, ".agents/skills/bad/skill-package.toml")[
            "required_gaps"
        ]
    )
    manifest = write_skill(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("sha256:", "sha256:0", 1), encoding="utf-8"
    )
    assert (
        "skill_package_expected_digest_invalid:sample"
        in sp.validate_skill_package_manifest(tmp_path, manifest.relative_to(tmp_path).as_posix())[
            "required_gaps"
        ]
    )
    path = tmp_path / "SKILL.md"
    path.write_text("# No frontmatter\n\n## When to Use\nTBD\n", encoding="utf-8")
    gaps = sp.validate_skill_markdown(
        tmp_path,
        "SKILL.md",
        "sample",
        ["When to Use", "Workflow"],
        placeholder_allowed=False,
    )["required_gaps"]
    assert "skill_quality_missing_frontmatter:sample" in gaps
    assert "skill_quality_missing_section:sample:Workflow" in gaps
    assert "skill_quality_missing_truth_boundary:sample" in gaps
    assert "skill_quality_placeholder_section:sample:When to Use" in gaps


def test_capability_semantics_and_helpers(tmp_path: Path) -> None:
    gaps, records = sp._capability_records(
        "sample",
        [
            {"id": "bad-kind", "kind": "unknown"},
            {"id": "bad-command", "kind": "command_readonly", "command": ["git", "status"]},
            {"id": "mutating-read", "kind": "command_readonly", "command": ["ethos", "land"]},
            {"id": "bad-proof", "kind": "command_proof", "command": ["ethos", "status"]},
            {"id": "unguarded", "kind": "script_mutation_guarded", "command": ["script.sh"]},
            {"id": "invalid-command", "kind": "command_readonly", "command": ["ethos", 1]},
            "not-a-dict",
        ],
    )
    assert records
    for expected in (
        "skill_package_capability_kind_unknown:sample:unknown",
        "skill_package_capability_readonly_untrusted:sample:bad-command",
        "skill_package_capability_readonly_mutating:sample:mutating-read",
        "skill_package_capability_proof_invalid:sample:bad-proof",
        "skill_package_capability_guard_missing:sample:unguarded",
        "skill_package_capability_command_invalid:sample:5",
        "skill_package_capability_invalid:sample:6",
    ):
        assert expected in gaps
    package = tmp_path / "pkg"
    package.mkdir()
    assert sp._contained_package_path(package, "SKILL.md") is True
    assert sp._contained_package_path(package, "/tmp/outside") is False
    assert sp._contained_package_path(package, "../outside") is False
    assert sp._frontmatter_ok("---\nname: x\ndescription: y\n---\n") is True
    assert sp._section_body("## A\nbody\n## B\nnext", "A") == "body"
    assert sp._is_placeholder_body(" Coming soon. ") is True
    assert sp._string_list(["a", 2, ""]) == ["a", "2"]
