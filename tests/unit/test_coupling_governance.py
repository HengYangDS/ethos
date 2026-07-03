from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import ethos_repository.coupling as coupling
from ethos_repository.coupling import coupling_audit_report

if TYPE_CHECKING:
    import pytest


def test_coupling_audit_keeps_git_native_and_classifies_provider_layers() -> None:
    report = coupling_audit_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert list(report["taxonomy"]) == [
        "product_semantic_hard_binding",
        "mandatory_governance_dependency",
        "native_protocol_binding",
        "product_toolchain_binding",
        "profile_or_adapter_binding",
        "default_policy",
        "historical_evidence",
        "test_fixture",
    ]
    assert report["git_native"] == {
        "strongly_bound": True,
        "layer": "product_semantic_hard_binding",
        "allowed_terms": [
            "Git",
            "git",
            "worktree",
            "branch",
            "refs",
            "HEAD",
            "role_policy",
        ],
        "not_a_generic_vcs_abstraction": True,
    }
    assert "candidate/dev" not in report["git_native"]["allowed_terms"]
    assert "work/*" not in report["git_native"]["allowed_terms"]
    assert "submit/*" not in report["git_native"]["allowed_terms"]
    assert report["openspec_governance"] == {
        "required": True,
        "layer": "mandatory_governance_dependency",
        "capability": "official-native governance records",
        "execution_surface": "profile_or_adapter_binding",
        "not_a_second_command_plane": True,
    }
    assert report["native_protocols"] == {
        "layer": "native_protocol_binding",
        "formats": ["JSON Schema", "command JSON", "TOML", "JSONL", "SQLite local state"],
        "provider_optional": False,
    }
    registry = {entry["id"]: entry for entry in report["binding_registry"]}
    assert list(registry) == [
        "git_repository_substrate",
        "branch_role_policy",
        "work_lane_lifecycle_command_contract",
        "openspec_workspace",
        "openspec_cli",
        "command_json_schema_protocol",
        "claims_evidence_digest_protocol",
        "sqlite_local_state_protocol",
        "uv_workspace_toolchain",
        "hatchling_build_backend",
        "pytest_test_runner",
        "ruff_lint_runner",
        "gitlab_release_profile",
        "mcp_acp_protocol_adapters",
        "npm_launcher_distribution_adapter",
        "historical_evidence_records",
        "provider_test_fixtures",
    ]
    assert registry["git_repository_substrate"]["layer"] == "product_semantic_hard_binding"
    assert registry["git_repository_substrate"]["required"] is True
    assert registry["git_repository_substrate"]["owns_product_semantics"] is True
    assert registry["git_repository_substrate"]["adapter_replaceable"] is False
    assert registry["git_repository_substrate"]["surfaces"] == [
        "commits",
        "refs",
        "branches",
        "worktrees",
        "HEAD",
    ]
    assert registry["branch_role_policy"]["config_source"] == ".ethos/workspace.toml"
    assert registry["branch_role_policy"]["config_keys"] == [
        "release_branch",
        "accepted_branch",
        "candidate_branch",
        "work_branch_prefix",
        "submit_branch_prefix",
    ]
    assert registry["branch_role_policy"]["default_policy"] is False
    assert registry["branch_role_policy"]["role_order"] == [
        "release_root",
        "accepted_root",
        "candidate",
        "work_lane",
        "submit_lane",
    ]
    assert registry["branch_role_policy"]["configured_patterns"] == [
        "main",
        "dev",
        "candidate/dev",
        "work/*",
        "submit/*",
    ]
    assert registry["work_lane_lifecycle_command_contract"]["commands"] == [
        "ethos lane start",
        "ethos lane prewrite",
        "ethos lane bind-claim",
        "ethos lane refresh-base",
        "ethos land",
        "ethos land --closeout",
        "ethos lane retire-landed",
    ]
    assert registry["work_lane_lifecycle_command_contract"]["forbidden_workflow_state"] == [
        "raw_git_worktree_add"
    ]
    assert registry["openspec_workspace"]["not_a_second_command_plane"] is True
    assert registry["openspec_workspace"]["not_product_substrate"] is True
    assert registry["openspec_cli"]["surfaces"] == [
        "official OpenSpec status",
        "official OpenSpec strict validation",
    ]
    assert registry["openspec_cli"]["not_a_second_command_plane"] is True
    assert registry["openspec_cli"]["not_product_substrate"] is True
    assert registry["uv_workspace_toolchain"]["layer"] == "product_toolchain_binding"
    assert registry["hatchling_build_backend"]["layer"] == "product_toolchain_binding"
    assert registry["pytest_test_runner"]["layer"] == "product_toolchain_binding"
    assert registry["ruff_lint_runner"]["layer"] == "product_toolchain_binding"
    assert registry["gitlab_release_profile"]["layer"] == "profile_or_adapter_binding"
    assert registry["mcp_acp_protocol_adapters"]["layer"] == "profile_or_adapter_binding"
    assert registry["npm_launcher_distribution_adapter"]["layer"] == (
        "profile_or_adapter_binding"
    )
    assert report["release_product_files"] == [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".ethos/release.toml",
    ]
    assert report["release_host_profile"]["provider"] == "gitlab"
    assert report["release_host_profile"]["layer"] == "profile_or_adapter_binding"
    assert report["product_toolchain"] == {
        "profile": "product-toolchain",
        "layer": "product_toolchain_binding",
        "gates": ["unit-architecture", "ruff", "build"],
        "toolchains": ["uv-python"],
        "product_ontology_anchor": False,
    }


def test_work_lane_lifecycle_binding_excludes_raw_git_worktree_entrypoint() -> None:
    report = coupling_audit_report(Path.cwd())
    registry = {entry["id"]: entry for entry in report["binding_registry"]}
    lifecycle = registry["work_lane_lifecycle_command_contract"]

    assert lifecycle["commands"] == [
        "ethos lane start",
        "ethos lane prewrite",
        "ethos lane bind-claim",
        "ethos lane refresh-base",
        "ethos land",
        "ethos land --closeout",
        "ethos lane retire-landed",
    ]
    assert lifecycle["forbidden_workflow_state"] == ["raw_git_worktree_add"]
    assert "git worktree add" not in lifecycle["commands"]
    assert lifecycle["layer"] == "product_semantic_hard_binding"
    assert lifecycle["owns_product_semantics"] is True


def test_binding_registry_keeps_each_binding_in_its_mechanism_layer() -> None:
    report = coupling_audit_report(Path.cwd())
    registry = {entry["id"]: entry for entry in report["binding_registry"]}

    assert registry["git_repository_substrate"]["layer"] == (
        "product_semantic_hard_binding"
    )
    assert registry["branch_role_policy"]["layer"] == "product_semantic_hard_binding"
    assert registry["work_lane_lifecycle_command_contract"]["layer"] == (
        "product_semantic_hard_binding"
    )
    assert registry["openspec_workspace"]["layer"] == "mandatory_governance_dependency"
    assert registry["openspec_cli"]["layer"] == "mandatory_governance_dependency"
    for binding_id in (
        "uv_workspace_toolchain",
        "hatchling_build_backend",
        "pytest_test_runner",
        "ruff_lint_runner",
    ):
        assert registry[binding_id]["layer"] == "product_toolchain_binding"
        assert registry[binding_id]["owns_product_semantics"] is False
        assert registry[binding_id]["adapter_replaceable"] is True
    for binding_id in (
        "gitlab_release_profile",
        "mcp_acp_protocol_adapters",
        "npm_launcher_distribution_adapter",
    ):
        assert registry[binding_id]["layer"] == "profile_or_adapter_binding"
        assert registry[binding_id]["owns_product_semantics"] is False
    assert registry["historical_evidence_records"]["layer"] == "historical_evidence"
    assert registry["provider_test_fixtures"]["layer"] == "test_fixture"


def test_coupling_report_has_no_self_or_legacy_current_surface_terms() -> None:
    report = coupling_audit_report(Path.cwd())

    rendered = json.dumps(report, sort_keys=True)
    assert not hasattr(coupling, "SELF_HOSTING_GATES")
    assert "self_hosting" not in rendered
    assert "legacy" not in rendered


def test_binding_registry_exposes_substantive_binding_contract_metadata() -> None:
    report = coupling_audit_report(Path.cwd())

    for entry in report["binding_registry"]:
        assert entry["required_for"]
        assert entry["replaceability"] in {
            "hard-bound",
            "mandatory",
            "replaceable-adapter",
            "historical",
            "fixture-only",
        }
        assert entry["degradation_state"]
        assert entry["proof_gate"]

    registry = {entry["id"]: entry for entry in report["binding_registry"]}
    assert registry["git_repository_substrate"]["replaceability"] == "hard-bound"
    assert registry["git_repository_substrate"]["required_for"] == [
        "repository identity",
        "branch roles",
        "HEAD-bound evidence",
        "worktree lifecycle",
    ]
    assert registry["openspec_workspace"]["replaceability"] == "mandatory"
    assert registry["openspec_workspace"]["required_for"] == [
        "official governance records",
        "strict specification validation",
    ]
    assert registry["gitlab_release_profile"]["replaceability"] == "replaceable-adapter"


def test_coupling_audit_branch_role_policy_reports_config_source(tmp_path: Path) -> None:
    workspace = tmp_path / ".ethos" / "workspace.toml"
    workspace.parent.mkdir(parents=True)
    workspace.write_text(
        "[branch_roles]\n"
        'release_branch = "release"\n'
        'accepted_branch = "integration"\n'
        'candidate_branch = "stage/integration"\n'
        'work_branch_prefix = "lane/"\n'
        'submit_branch_prefix = "review/"\n',
        encoding="utf-8",
    )

    report = coupling_audit_report(tmp_path)

    registry = {entry["id"]: entry for entry in report["binding_registry"]}
    assert registry["branch_role_policy"]["config_source"] == ".ethos/workspace.toml"
    assert registry["branch_role_policy"]["config_keys"] == [
        "release_branch",
        "accepted_branch",
        "candidate_branch",
        "work_branch_prefix",
        "submit_branch_prefix",
    ]
    assert registry["branch_role_policy"]["default_policy"] is False
    assert registry["branch_role_policy"]["role_order"] == [
        "release_root",
        "accepted_root",
        "candidate",
        "work_lane",
        "submit_lane",
    ]
    assert registry["branch_role_policy"]["configured_patterns"] == [
        "release",
        "integration",
        "stage/integration",
        "lane/*",
        "review/*",
    ]


def test_coupling_audit_default_branch_role_policy_marks_default_source(
    tmp_path: Path,
) -> None:
    report = coupling_audit_report(tmp_path)

    registry = {entry["id"]: entry for entry in report["binding_registry"]}

    assert registry["branch_role_policy"]["config_source"] == ".ethos/workspace.toml"
    assert registry["branch_role_policy"]["default_policy"] is True


def test_coupling_audit_flags_missing_work_lane_lifecycle_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_registry = coupling._binding_registry

    def registry_without_lifecycle(root: Path) -> list[dict[str, object]]:
        return [
            entry
            for entry in original_registry(root)
            if entry["id"] != "work_lane_lifecycle_command_contract"
        ]

    monkeypatch.setattr(coupling, "_binding_registry", registry_without_lifecycle)

    report = coupling_audit_report(Path.cwd())

    assert report["ok"] is False
    assert "binding_registry_missing:work_lane_lifecycle_command_contract" in (
        report["required_gaps"]
    )


def test_coupling_audit_flags_missing_git_product_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_registry = coupling._binding_registry

    def registry_without_git(root: Path) -> list[dict[str, object]]:
        return [
            entry
            for entry in original_registry(root)
            if entry["id"] != "git_repository_substrate"
        ]

    monkeypatch.setattr(coupling, "_binding_registry", registry_without_git)

    report = coupling_audit_report(Path.cwd())

    assert report["ok"] is False
    assert "binding_registry_missing:git_repository_substrate" in report["required_gaps"]


def test_coupling_audit_flags_openspec_as_product_substrate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_registry = coupling._binding_registry

    def registry_with_wrong_openspec_layer(root: Path) -> list[dict[str, object]]:
        entries = original_registry(root)
        for entry in entries:
            if entry["id"] == "openspec_workspace":
                entry["layer"] = "product_semantic_hard_binding"
                entry["owns_product_semantics"] = True
                entry["not_product_substrate"] = False
        return entries

    monkeypatch.setattr(coupling, "_binding_registry", registry_with_wrong_openspec_layer)

    report = coupling_audit_report(Path.cwd())

    assert report["ok"] is False
    assert "binding_registry_layer:openspec_workspace:product_semantic_hard_binding" in (
        report["required_gaps"]
    )
    assert "binding_registry_product_semantics:openspec_workspace" in (
        report["required_gaps"]
    )
    assert "binding_registry_product_substrate:openspec_workspace" in (
        report["required_gaps"]
    )


def test_coupling_audit_flags_adapter_owning_product_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_registry = coupling._binding_registry

    def registry_with_adapter_semantics(root: Path) -> list[dict[str, object]]:
        entries = original_registry(root)
        for entry in entries:
            if entry["id"] == "npm_launcher_distribution_adapter":
                entry["owns_product_semantics"] = True
                entry["action"] = "checkout"
        return entries

    monkeypatch.setattr(coupling, "_binding_registry", registry_with_adapter_semantics)

    report = coupling_audit_report(Path.cwd())

    assert report["ok"] is False
    assert "binding_registry_product_semantics:npm_launcher_distribution_adapter" in (
        report["required_gaps"]
    )
    assert "binding_registry_ui_projection:npm_launcher_distribution_adapter:action" in (
        report["required_gaps"]
    )


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


def test_coupling_audit_flags_additional_model_editor_and_host_vendor_names(
    tmp_path: Path,
) -> None:
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
        "JetBrains, Anthropic, Gemini, Copilot, Cursor, and Windsurf are examples.\n",
        encoding="utf-8",
    )

    report = coupling_audit_report(tmp_path)

    assert "product_vendor_term:docs/governance/product-design-contract.md:JetBrains" in (
        report["required_gaps"]
    )
    assert "product_vendor_term:docs/governance/product-design-contract.md:Anthropic" in (
        report["required_gaps"]
    )
    assert "product_vendor_term:docs/governance/product-design-contract.md:Gemini" in (
        report["required_gaps"]
    )
    assert "product_vendor_term:docs/governance/product-design-contract.md:Copilot" in (
        report["required_gaps"]
    )
    assert "product_vendor_term:docs/governance/product-design-contract.md:Cursor" in (
        report["required_gaps"]
    )
    assert "product_vendor_term:docs/governance/product-design-contract.md:Windsurf" in (
        report["required_gaps"]
    )


def test_coupling_audit_flags_host_projection_labels_in_product_docs(
    tmp_path: Path,
) -> None:
    doc = tmp_path / "docs" / "reference" / "command-plane.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(
        "---\n"
        "subject: ethos:command-plane\n"
        "role: reference\n"
        "state: canonical\n"
        "relations: canonical_for: test\n"
        "---\n\n"
        "# Command Plane\n\n"
        "A host may show Open Worktree or Checkout, but product state cannot.\n",
        encoding="utf-8",
    )

    report = coupling_audit_report(tmp_path)

    assert "product_host_projection_term:docs/reference/command-plane.md:Open Worktree" in (
        report["required_gaps"]
    )
    assert "product_host_projection_term:docs/reference/command-plane.md:Checkout" in (
        report["required_gaps"]
    )
