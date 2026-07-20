import ethos.assistants.skills.capabilities as c
import ethos.assistants.skills.packages as p


def test_capability_and_package_edges(tmp_path) -> None:
    items = [None, {"kind": "unknown"}, {"kind": "command_readonly", "command": ["ethos", 1]}, {"kind": "command_proof"}]  # fmt: skip
    gaps, _records = c.capability_records("s", items)
    joined = " ".join(gaps)
    assert all(term in joined for term in ("capability_invalid", "kind_unknown", "command_invalid", "command_missing"))  # fmt: skip
    contexts = [c.CapabilityValidationContext("s", "c", "script_readonly", command, {}, tmp_path, frozenset()) for command in ([], ["."], ["python3"])]  # fmt: skip
    assert not any(map(c.is_trusted_readonly_script, contexts))
    assert not c.is_mutating_command([])
    assert not c.contained_package_path(tmp_path, tmp_path.as_posix())
    package = tmp_path / ".agents/skills/bad"
    package.mkdir(parents=True)
    (package / "package.toml").write_text("[[bad]\n", encoding="utf-8")
    report = p.validate_skill_package_manifest(tmp_path, ".agents/skills/bad/package.toml")
    assert report["required_gaps"] == ["skill_package_manifest_invalid_toml:bad"]
    assert p.validate_skill_markdown(tmp_path, "missing.md", "s")["required_gaps"] == ["skill_missing_file:s"]  # fmt: skip
    schema = {"schema_version": 2, "digest_algorithm": "sha256", "expected_digest": "sha256:" + "0" * 64}  # fmt: skip
    assert set(p._manifest_schema_gaps("s", schema)) == {"skill_package_include_missing:s", "skill_package_required_sections_missing:s"}  # fmt: skip
    long = "---\nname: s\ndescription: Use when " + "x " * 70 + "\n---\n"
    assert p._frontmatter_gaps("s", long) == ["skill_quality_description_too_long:s"]
    disclosure = p._progressive_disclosure_gaps("s", "## Workflow\n" + "1. x\n" * 199)
    assert len(disclosure) == 3
    assert all(term in " ".join(disclosure) for term in ("entrypoint_too_long", "workflow_too_many_steps"))  # fmt: skip
    bad = "---\nname: s\ndescription: x\n"
    assert (p._frontmatter_header(bad), p._frontmatter_ok(bad)) == ("", False)
