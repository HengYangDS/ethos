# ruff: noqa: TC003
"""Coverage-closure edge tests for the assistants cluster (100% no-exemption campaign)."""

from __future__ import annotations

from pathlib import Path

from ethos.assistants import skill_packages as sp


def test_validate_skill_markdown_missing_file(tmp_path: Path) -> None:
    # path resolves under root but the file does not exist -> FileNotFoundError
    # fallback at lines 201-202.
    result = sp.validate_skill_markdown(tmp_path, "nope/missing.md", "ghost")
    assert result == {"ok": False, "required_gaps": ["skill_missing_file:ghost"]}


def test_manifest_schema_gaps_flags_missing_include() -> None:
    # `include` key absent -> _string_list -> [] -> `if not include` -> line 294.
    gaps = sp._manifest_schema_gaps(
        "sample",
        {
            "schema_version": sp.SKILL_PACKAGE_SCHEMA_VERSION,
            "digest_algorithm": "sha256",
            "expected_digest": "sha256:" + "0" * 64,
            "required_sections": ["When to Use"],
        },
    )
    assert "skill_package_include_missing:sample" in gaps


def test_manifest_schema_gaps_flags_missing_required_sections() -> None:
    # `required_sections` key absent -> _string_list -> [] -> line 302.
    gaps = sp._manifest_schema_gaps(
        "sample",
        {
            "schema_version": sp.SKILL_PACKAGE_SCHEMA_VERSION,
            "digest_algorithm": "sha256",
            "include": ["SKILL.md"],
            "expected_digest": "sha256:" + "0" * 64,
        },
    )
    assert "skill_package_required_sections_missing:sample" in gaps


def test_is_trusted_readonly_script_rejects_empty_command(tmp_path: Path) -> None:
    context = sp.CapabilityValidationContext(
        skill_id="s",
        capability_id="c",
        kind="script_readonly",
        command=[],
        item={},
        package_dir=tmp_path,
        included_files=frozenset(),
    )
    assert sp._is_trusted_readonly_script(context) is False  # line 340


def test_is_trusted_readonly_script_rejects_flag_or_dot(tmp_path: Path) -> None:
    for bad in ("--flag", ".", ".."):
        context = sp.CapabilityValidationContext(
            skill_id="s",
            capability_id="c",
            kind="script_readonly",
            command=[bad],
            item={},
            package_dir=tmp_path,
            included_files=frozenset(),
        )
        assert sp._is_trusted_readonly_script(context) is False  # line 343


def test_is_trusted_readonly_script_rejects_interpreter_prefix(tmp_path: Path) -> None:
    # `python3` is included and package-contained, so only the interpreter guard
    # at line 345 can produce False.
    context = sp.CapabilityValidationContext(
        skill_id="s",
        capability_id="c",
        kind="script_readonly",
        command=["python3", "audit.py"],
        item={},
        package_dir=tmp_path,
        included_files=frozenset({"python3"}),
    )
    assert sp._is_trusted_readonly_script(context) is False  # line 345


def test_frontmatter_gaps_flags_overlong_description() -> None:
    long_desc = "Use when " + " ".join(f"word{index}" for index in range(70))
    text = f"---\nname: sample\ndescription: {long_desc}\n---\n\n# Body\n"
    gaps = sp._frontmatter_gaps("sample", text)
    assert "skill_quality_description_too_long:sample" in gaps  # line 410


def test_progressive_disclosure_gaps_flags_overlong_entrypoint() -> None:
    text = "\n".join(f"line {index}" for index in range(200))
    gaps = sp._progressive_disclosure_gaps("sample", text)
    assert any(
        gap.startswith("skill_quality_entrypoint_too_long:sample:") for gap in gaps
    )  # line 418


def test_progressive_disclosure_gaps_flags_too_many_workflow_steps() -> None:
    steps = "\n".join(f"{index}. Step {index}" for index in range(1, 11))
    text = f"## Workflow\n{steps}\n"
    gaps = sp._progressive_disclosure_gaps("sample", text)
    assert any(
        gap.startswith("skill_quality_workflow_too_many_steps:sample:") for gap in gaps
    )  # line 424


def test_frontmatter_header_returns_empty_when_unterminated() -> None:
    # Opens with '---\n' but has no closing delimiter -> split yields < 3 parts.
    assert sp._frontmatter_header("---\nname: x\ndescription: y\n") == ""  # line 437


def test_frontmatter_ok_false_when_unterminated() -> None:
    # Opens with '---\n' but never closes -> split yields < 3 parts -> line 446.
    assert sp._frontmatter_ok("---\nname: x\ndescription: y\n") is False


def test_string_list_returns_empty_for_non_list() -> None:
    assert sp._string_list(None) == []  # line 468
    assert sp._string_list("SKILL.md") == []
