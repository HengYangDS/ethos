from __future__ import annotations

from pathlib import Path

from ethos_repository.coupling import coupling_audit_report


def test_coupling_audit_keeps_git_native_and_classifies_provider_layers() -> None:
    report = coupling_audit_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert list(report["taxonomy"]) == [
        "product_semantic",
        "default_policy",
        "profile_config",
        "adapter_projection",
        "self_hosting_evidence",
        "legacy_evidence",
        "test_fixture",
    ]
    assert report["git_native"] == {
        "strongly_bound": True,
        "layer": "product_semantic",
        "allowed_terms": [
            "Git",
            "git",
            "worktree",
            "branch",
            "candidate/dev",
            "work/*",
            "submit/*",
        ],
        "not_a_generic_vcs_abstraction": True,
    }
    assert report["release_product_files"] == [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".ethos/release.toml",
    ]
    assert report["release_host_profile"]["provider"] == "gitlab"
    assert report["release_host_profile"]["layer"] == "profile_config"
    assert report["self_hosting_toolchain"] == {
        "profile": "self-hosting",
        "layer": "self_hosting_evidence",
        "gates": ["unit-architecture", "ruff", "build"],
        "toolchains": ["uv-python"],
    }


def test_coupling_audit_flags_model_and_editor_terms_in_product_docs(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "governance" / "product-design-contract.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "---\n"
        "subject: ethos:product-design-contract\n"
        "role: policy\n"
        "state: canonical\n"
        "relations: canonical_for: test\n"
        "---\n\n"
        "# Product Design Contract\n\n"
        "OpenAI model names and IDE labels do not belong in product semantics.\n",
        encoding="utf-8",
    )

    report = coupling_audit_report(tmp_path)

    assert "product_vendor_term:docs/governance/product-design-contract.md:OpenAI" in (
        report["required_gaps"]
    )
    assert "product_vendor_term:docs/governance/product-design-contract.md:IDE" in (
        report["required_gaps"]
    )
    assert not any(
        "product_vendor_term" in gap and ":Git" in gap for gap in report["required_gaps"]
    )
