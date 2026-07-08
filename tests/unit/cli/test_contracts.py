from __future__ import annotations

import json
import re
from pathlib import Path

from ethos.domain.report import _advisory_next_actions
from ethos.domain.report import _gap_layers
from ethos.repository.adoption.planner import adoption_plan
from ethos_core.contracts.package_ontology import package_ontology_report
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw


def test_status_json_contract() -> None:
    payload = run_ethos("status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "status"
    assert payload["state"] in {"ready", "dirty"}
    assert payload["next_actions"]


def test_quality_package_ontology_reports_migration_state() -> None:
    payload = run_ethos("quality", "package-ontology", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality package-ontology"
    assert payload["data"]["migration_complete"] is True
    assert payload["data"]["migration_status"] == "complete"
    assert "ethos" in payload["data"]["target_packages"]
    assert "ethos-core" in payload["data"]["target_packages"]
    assert "ethos" not in payload["data"]["migration_hosts"]
    assert payload["data"]["distribution_status"]["distributions/npm"]["state"] == ("migrated")


def test_quality_asset_policy_command_reports_mechanical_quality_assets() -> None:
    payload = run_ethos("quality", "asset-policy", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality asset-policy"
    assert payload["state"] == "clean"
    assert payload["summary"]["asset_class_count"] >= 9
    asset_classes = {asset["class"] for asset in payload["data"]["asset_classes"]}
    assert {"python-code", "markdown-docs", "shell-scripts", "toml-config"} <= asset_classes


def test_quality_docs_command_reports_docs_profile_dimensions() -> None:
    payload = run_ethos("quality", "docs", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality docs"
    assert payload["state"] == "clean"
    checks = {check["id"]: check for check in payload["data"]["profile"]["checks"]}
    assert checks["link-integrity"]["tool_adapter"] == "lychee"
    assert checks["reader-purpose"]["dimensions"] == ["status", "purpose", "see_also"]
    assert payload["data"]["style_goals"] == ["faithful", "expressive", "elegant"]


def test_quality_proof_policy_command_reports_lattice() -> None:
    payload = run_ethos("quality", "proof-policy", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality proof-policy"
    assert payload["state"] == "clean"
    states = {state["state"]: state for state in payload["data"]["states"]}
    assert states["planned"]["trust_bearing"] is False
    assert states["proven"]["trust_bearing"] is True
    assert payload["data"]["trust_consumers"] == [
        "claim",
        "land",
        "publish",
        "release",
        "repository-governance",
    ]


def test_quality_tool_profiles_command_reports_adapter_boundaries() -> None:
    payload = run_ethos("quality", "tool-profiles", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality tool-profiles"
    adapters = {adapter["id"]: adapter for adapter in payload["data"]["tool_adapters"]}
    assert adapters["ruff"]["asset_classes"] == ["python-code"]
    assert adapters["lychee"]["asset_classes"] == ["markdown-docs"]
    assert adapters["shellcheck"]["asset_classes"] == ["shell-scripts"]
    assert adapters["taplo"]["asset_classes"] == ["toml-config"]
    assert adapters["ethos-docstrings-google"]["asset_classes"] == ["python-code"]
    assert adapters["ethos-module-layout"]["asset_classes"] == ["python-code"]


def test_quality_docs_registry_surfaces_all_required_gaps(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "---\nsubject: sample:guide\nrole: how-to\nstate: active\nrelations: {}\n---\n\n# Guide\n\nBody without required visible sections.",
        encoding="utf-8",
    )

    payload = run_ethos(
        "quality",
        "docs-registry",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["required_gaps"] == [
        "missing_visible_section:docs/guide.md:status",
        "missing_visible_section:docs/guide.md:purpose",
        "missing_visible_section:docs/guide.md:see also",
    ]
    assert payload["data"]["required_gaps"] == payload["required_gaps"]


def test_emit_handles_closed_pipes(monkeypatch) -> None:
    import builtins

    from ethos.surface.cli._base import emit
    from ethos_core.result import EthosResult

    def closed_pipe(*args, **kwargs) -> None:
        raise BrokenPipeError

    monkeypatch.setattr(builtins, "print", closed_pipe)

    emit(EthosResult(command="status", ok=True, state="ready"), json_output=True)


def test_quality_package_ontology_rejects_retired_workspace_config(
    tmp_path: Path,
) -> None:
    for package in package_ontology_report()["target_packages"]:
        (tmp_path / "packages" / str(package)).mkdir(parents=True)
    (tmp_path / "distributions" / "npm").mkdir(parents=True)
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "workspace.toml").write_text(
        '[[package]]\nname = "ethos-kernel"\npath = "packages/ethos-kernel"\n',
        encoding="utf-8",
    )

    completed = run_ethos_raw(
        "quality",
        "package-ontology",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert payload["ok"] is False
    assert "workspace_config_retired_product_family:ethos-kernel" in payload["required_gaps"]


def test_status_json_reports_live_workspace_schema_validation() -> None:
    payload = run_ethos("status", "--json")

    validations = [
        diagnostic
        for diagnostic in payload["diagnostics"]
        if diagnostic.get("kind") == "schema_validation"
    ]
    assert validations == [
        {
            "kind": "schema_validation",
            "target": "data",
            "schema": "workspace-status.schema.json",
            "ok": True,
            "required_gaps": [],
        }
    ]
    assert "schema_validation" not in payload["data"]


def test_plan_changed_returns_action_graph() -> None:
    payload = run_ethos("plan", "--changed", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "plan"
    assert "action_graph" in payload["data"]


def test_plan_changed_maps_repository_rules_to_required_gates(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    rules = repo / ".ethos" / "rules.toml"
    rules.write_text(
        """
[gates.unit]
command = "pytest tests/unit"
blocking = true

[[rule]]
id = "python-source"
risk = "source-change"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit-test"]
""".lstrip(),
        encoding="utf-8",
    )
    source = repo / "src" / "demo.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-gpg-sign",
        "--no-verify",
        "-m",
        "add governed source",
    )
    source.write_text("VALUE = 2\n", encoding="utf-8")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert payload["summary"]["matched_rule_count"] == 1
    assert payload["summary"]["required_gate_count"] == 1
    assert payload["data"]["matched_rules"][0]["id"] == "python-source"
    assert payload["data"]["matched_rules"][0]["matched_paths"] == ["src/demo.py"]
    assert payload["data"]["required_gates"] == [
        {"id": "unit", "command": "pytest tests/unit", "blocking": True}
    ]


def test_plan_changed_reports_adopter_contract_profile_matches(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    rules = repo / ".ethos" / "rules.toml"
    rules.write_text(
        """
[gates.raw_changed]
command = "nox -s raw_changed"
blocking = true

[[contract_profile]]
id = "dmgr"
policy = "rules/dmgr/contracts.toml"

[[rule]]
id = "dmgr-raw-cache"
risk = "raw-cache-contract"
paths = ["packages/dmgr-cache/**"]
requires = ["raw_changed"]
evidence = ["cache-tree"]
""".lstrip(),
        encoding="utf-8",
    )
    contracts = repo / "rules" / "dmgr" / "contracts.toml"
    contracts.parent.mkdir(parents=True)
    contracts.write_text(
        """
[[contract]]
id = "cache-shape-metadata-sidecars-checkpoint"
surface = "cache"
paths = ["packages/dmgr-cache/**"]
protects = ["NIO cache shape"]
required_evidence = ["cache-tree"]
""".lstrip(),
        encoding="utf-8",
    )
    source = repo / "packages" / "dmgr-cache" / "src" / "dmgr_cache" / "__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text('"""Cache package."""\n', encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--no-gpg-sign",
        "--no-verify",
        "-m",
        "add adopter profile",
    )
    source.write_text('"""Cache package."""\nVALUE = 1\n', encoding="utf-8")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert payload["data"]["matched_rules"][0]["id"] == "dmgr-raw-cache"
    assert payload["data"]["domain_contracts"] == [
        {
            "profile": "dmgr",
            "contract": "cache-shape-metadata-sidecars-checkpoint",
            "surface": "cache",
            "matched_paths": ["packages/dmgr-cache/src/dmgr_cache/__init__.py"],
            "protects": ["NIO cache shape"],
            "required_evidence": ["cache-tree"],
        }
    ]


def test_assistants_doctor_accepts_root_for_shadow_parity(tmp_path: Path) -> None:
    payload = run_ethos("assistants", "doctor", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "assistants doctor"


def test_repository_audit_reports_governed_repository_shape() -> None:
    payload = run_ethos("audit", "--mode", "shape", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "audit"
    context = payload["data"]["governance_context"]
    assert context["contract"] == "governed_repository"
    assert context["profile"] == "product"
    assert context["single_kernel"] is True
    assert context["kernel_chain"] == [
        "Authority",
        "Subject",
        "Commitment",
        "Change",
        "Evidence",
        "Claim",
        "Chronicle",
    ]
    # The head-of-chain nodes are real kernel models, not an inline dict — the
    # Authority carries the authority order and the Subject is the governed repo.
    assert context["authority"]["order_ref"] == "system/authority.toml"
    assert context["authority"]["policy_refs"][0] == "user_instruction"
    assert context["subject"]["kind"] == "repository"
    assert context["subject"]["id"] == str(Path.cwd())
    assert context["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert context["reader_view_commands"] == ["ethos orient"]
    assert context["scorecard_commands"] == ["ethos report"]
    assert context["truth_boundary"] == "repository"
    assert context["profile_boundary"] == "profile_or_adapter"
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["data"]["openspec"]["mode"] == "shape"
    assert payload["required_gaps"] == []
    package_ontology = payload["data"]["package_ontology"]
    assert package_ontology["ok"] is True
    assert "canonical_packages" not in package_ontology
    assert package_ontology["migration_host_packages"] == []
    assert "ethos-core" in package_ontology["target_package_contract"]


def test_repository_audit_rejects_invalid_mode_as_json_gap() -> None:
    payload = run_ethos("audit", "--mode", "fastish", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "invalid"
    assert payload["required_gaps"] == ["invalid_audit_mode:fastish"]


def test_quality_command_registry_rejects_retired_public_roots() -> None:
    payload = run_ethos("quality", "command-registry", "--json")

    assert payload["ok"] is True
    assert payload["data"]["retired_public_roots"] == []
    assert payload["data"]["retired_public_root_mentions"] == []
    assert "ethos status" in payload["data"]["public_commands"]
    assert "ethos intake" not in payload["data"]["public_commands"]
    assert "ethos lane" not in payload["data"]["public_commands"]
    assert "ethos parity" not in payload["data"]["public_commands"]
    assert "ethos intake" in payload["data"]["known_commands"]
    assert "ethos lane" in payload["data"]["known_commands"]
    assert "ethos parity" in payload["data"]["known_commands"]


def test_root_help_foregrounds_workflow_and_hides_maintainer_apps() -> None:
    completed = run_ethos_raw("--help")

    assert completed.returncode == 0
    assert "status" in completed.stdout
    assert "plan" in completed.stdout
    assert "prove" in completed.stdout
    assert "land" in completed.stdout
    assert "publish" in completed.stdout
    assert "report" in completed.stdout
    for maintainer in ("audit", "openspec", "quality", "campaign", "lane", "parity"):
        assert f"│ {maintainer} " not in completed.stdout
    for reference in ("doctor", "docs", "explain"):
        assert f"│ {reference} " not in completed.stdout


def test_quality_standard_registry_declares_adapter_boundaries() -> None:
    payload = run_ethos("quality", "standards", "--json")

    assert payload["ok"] is True
    adapters = payload["data"]["adapters"]
    for adapter in (
        "slsa",
        "sigstore",
        "opentelemetry",
        "dagger",
        "cue",
        "opa",
        "temporal",
        "mcp",
    ):
        assert adapter in adapters
        assert adapters[adapter]["boundary"]
        assert adapters[adapter]["fallback"]
        assert adapters[adapter]["exit_strategy"]


def test_quality_format_policy_reads_repository_policy() -> None:
    payload = run_ethos("quality", "format-policy", "--json")

    assert payload["ok"] is True
    assert payload["data"]["source"] == ".ethos/rules.toml"
    assert payload["data"]["artifacts"]["state_tracked_truth"] is False


def test_quality_schema_gate_and_commit_commands_are_available() -> None:
    for command in (
        ("quality", "schemas", "--json"),
        ("quality", "gates", "--json"),
        ("quality", "generated-artifacts", "--json"),
        ("quality", "docs-topology", "--json"),
        ("quality", "commits", "--json"),
        ("quality", "release", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_quality_help_lists_canonical_commands() -> None:
    completed = run_ethos_raw("quality", "--help")

    assert completed.returncode == 0
    commands = set(re.findall(r"^│\s+([a-z][a-z-]+)\s{2,}", completed.stdout, re.MULTILINE))
    assert commands == {
        "asset-policy",
        "claims",
        "code-size",
        "command-examples",
        "command-registry",
        "command-surface",
        "commits",
        "coupling-audit",
        "coverage",
        "docs",
        "docs-registry",
        "docs-topology",
        "docstrings",
        "evidence-freshness",
        "format-policy",
        "generated-artifacts",
        "gates",
        "markdown-links",
        "module-layout",
        "npm",
        "package-ontology",
        "projection-drift",
        "proof-policy",
        "provenance",
        "release",
        "release-attestation",
        "release-policy",
        "sbom",
        "schemas",
        "shell",
        "standards",
        "tool-profiles",
        "toml",
        "types",
        "yaml",
    }


def test_openspec_uses_official_native_cli(monkeypatch) -> None:
    import ethos.adapters.openspec.cli as openspec_cli

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        if args == ("doctor", "--json"):
            payload = {"root": {"healthy": True}}
        elif args == ("list", "--json"):
            payload = {"changes": [{"name": "ethos-release-hardening", "status": "in-progress"}]}
        elif args == ("status", "--change", "ethos-release-hardening", "--json"):
            payload = {"isComplete": True, "schemaName": "spec-driven"}
        elif args == ("validate", "--all", "--strict", "--json"):
            payload = {"items": [], "summary": {"totals": {"failed": 0}}}
        else:
            raise AssertionError(f"unexpected OpenSpec command: {args}")
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_cli, "run_json", fake_run_json)

    payload = run_ethos("openspec", "--change", "ethos-release-hardening", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "openspec"
    assert payload["data"]["official_cli"]["package"] == "@fission-ai/openspec"
    assert payload["data"]["schema_name"] == "spec-driven"
    assert payload["data"]["commands"]["validate"]["json"]["summary"]["totals"]["failed"] == 0


def test_openspec_lifecycle_flag_reports_lifecycle_summary(monkeypatch) -> None:
    def fake_report(root: Path, *, change: str | None = None, lifecycle: bool = False):
        return {
            "ok": True,
            "official_cli": {
                "package": "@fission-ai/openspec",
                "available": True,
                "base_command": ["openspec"],
            },
            "change": change,
            "schema_name": "spec-driven",
            "summary": {"change_count": 1, "validation": {}},
            "required_gaps": [],
            "commands": {},
            "lifecycle": {"enabled": lifecycle, "changes": []},
        }

    monkeypatch.setattr("ethos.surface.cli.root.reference.openspec_governance_report", fake_report)

    payload = run_ethos("openspec", "--change", "ethos-release-hardening", "--lifecycle", "--json")

    assert payload["ok"] is True
    assert payload["summary"]["lifecycle"] is True
    assert payload["data"]["lifecycle"] == {"enabled": True, "changes": []}


def test_full_gate_registry_includes_official_openspec_validation() -> None:
    payload = run_ethos("quality", "gates", "--json")

    assert payload["ok"] is True
    assert "self-audit" not in payload["data"]["gates"]
    assert payload["data"]["gates"]["repository-audit"]["command"][1:] == [
        "-m",
        "ethos.cli",
        "audit",
        "--mode",
        "shape",
        "--json",
    ]
    assert payload["data"]["gates"]["openspec"]["command"] == [
        "openspec",
        "validate",
        "--all",
        "--strict",
        "--json",
    ]
    assert payload["data"]["gates"]["python-types"]["command"] == [
        "ethos",
        "quality",
        "types",
        "--json",
    ]


def test_assistant_mcp_server_command_is_available() -> None:
    payload = run_ethos("assistants", "mcp-server", "--json")

    assert payload["ok"] is True
    assert payload["data"]["server"]["protocol"] == "mcp"


def test_fleet_inspect_reports_external_adopter_shape(tmp_path: Path) -> None:
    (tmp_path / ".gitlab").mkdir()
    adoption_plan(tmp_path, profile="gitlab", apply=True)

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "fleet inspect"
    assert payload["data"]["adopter"]["root"] == str(tmp_path.resolve())
    assert payload["data"]["adopter"]["governance"]["ethos_config"] is True
    assert payload["data"]["adopter"]["governance"]["openspec"] is True
    assert payload["data"]["adopter"]["governance"]["skills"] is True


def test_fleet_inspect_accepts_governed_docs_layout(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)
    (tmp_path / "docs" / "index.md").unlink()
    (tmp_path / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "governance" / "README.md").write_text(
        "---\nsubject: docs:governance\nrole: reference\nstate: canonical\nrelations: test\n---\n"
        "# Governance Docs\n",
        encoding="utf-8",
    )

    payload = run_ethos("fleet", "inspect", "--target", str(tmp_path), "--json")

    assert payload["ok"] is True
    assert payload["data"]["adopter"]["governance"]["docs"] is True


def test_quality_determinism_commands_are_available() -> None:
    for command in (
        ("quality", "command-surface", "--json"),
        ("quality", "format-policy", "--json"),
        ("quality", "projection-drift", "--json"),
        ("quality", "evidence-freshness", "--json"),
        ("quality", "command-examples", "--json"),
        ("quality", "coupling-audit", "--json"),
        ("quality", "docs-registry", "--json"),
        ("quality", "provenance", "--json"),
        ("quality", "claims", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_quality_coupling_audit_reports_git_native_boundary() -> None:
    payload = run_ethos("quality", "coupling-audit", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality coupling-audit"
    assert payload["required_gaps"] == []
    assert payload["data"]["git_native"]["strongly_bound"] is True
    assert payload["data"]["git_native"]["layer"] == "product_semantic_hard_binding"
    assert payload["data"]["openspec_governance"]["layer"] == ("mandatory_governance_dependency")
    assert payload["data"]["openspec_governance"]["not_a_second_command_plane"] is True
    assert payload["data"]["native_protocols"]["layer"] == "native_protocol_binding"
    assert payload["data"]["native_protocols"]["provider_optional"] is False
    assert payload["data"]["release_host_profile"]["provider"] == "gitlab"
    assert payload["data"]["product_toolchain"]["profile"] == "product-toolchain"
    assert payload["data"]["product_toolchain"]["layer"] == ("product_toolchain_binding")
    assert {
        "kind": "schema_validation",
        "target": "data",
        "schema": "coupling-audit.schema.json",
        "ok": True,
        "required_gaps": [],
    } in payload["diagnostics"]
    assert "schema_validation" not in payload["data"]


def test_report_uses_adopter_scorecard_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    payload = run_ethos("report", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["summary"]["governance_gap_count"] == 0
    assert payload["data"]["scores"]["adopter_governance"] == 1
    assert payload["data"]["first_hour"] == {
        "proof_status": "ready",
        "evidence_gap_count": 0,
        "land_readiness": "local_readiness",
        "publish_readiness": "local_readiness",
        "hosted_ci_truth": "external-evidence",
        "next_action": "ethos prove",
    }


def test_assistant_projection_commands_are_available() -> None:
    manifest = run_ethos("assistants", "mcp-manifest", "--json")
    projections = run_ethos("assistants", "check-projections", "--json")
    doctor = run_ethos("assistants", "doctor", "--json")

    assert manifest["ok"] is True
    assert "ethos.status" in manifest["data"]["manifest"]["tools"]
    assert projections["ok"] is True
    assert projections["data"]["contract"]["truth"] == "repository-source-and-contracts"
    assert doctor["ok"] is True


def test_intake_status_is_public_read_only_surface() -> None:
    payload = run_ethos("intake", "status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "intake status"
    assert payload["data"]["truth_boundary"] == "adopter-ledger"
    assert payload["data"]["projection"]["truth_boundary"] == "projection-evidence"
    assert payload["data"]["projection"]["repository_truth"] is False
    assert payload["data"]["provider"] == "unconfigured"


def test_intake_status_rejects_empty_configuration(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".ethos").mkdir(parents=True)
    (root / ".ethos" / "intake.toml").write_text("", encoding="utf-8")

    payload = run_ethos("intake", "status", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert payload["state"] == "invalid"
    assert payload["data"]["configured"] is False
    assert payload["data"]["provider"] == "invalid"
    assert "intake_provider_missing:.ethos/intake.toml" in payload["required_gaps"]


def test_docs_command_uses_registry_for_discovery() -> None:
    payload = run_ethos("docs", "agent-projections", "--json")

    assert payload["ok"] is True
    assert payload["data"]["path"] == "docs/architecture/agent-projections.md"


def test_report_advisory_layer_classifies_protected_openspec_residue() -> None:
    protected_residue_gap = (
        "openspec_protected_branch_active_change_unarchived:"
        "main:release_root:ethos-release-hardening"
    )
    next_actions = _advisory_next_actions((protected_residue_gap,))
    layers = _gap_layers(
        result_required_gaps=(),
        parity_gaps={"ok": True, "required_gaps": []},
        playbooks={"ok": True, "required_gaps": [], "advisory_gaps": []},
        advisory_gaps=(protected_residue_gap,),
        advisory_next_actions=next_actions,
    )

    advisory_layer = layers["advisory_signals"]
    assert advisory_layer["blocking"] is False
    assert advisory_layer["invalid_states"] == {
        "categories": {"carrier_invalid": [protected_residue_gap]},
        "category_count": 1,
        "gap_count": 1,
    }
    assert advisory_layer["next_actions"] == [
        "git ls-tree -r --name-only main -- openspec/changes/ethos-release-hardening",
        "ethos explain openspec_protected_branch_active_change_unarchived:main:release_root:ethos-release-hardening --json",
    ]


def test_report_scorecard_is_derived_from_governance_checks() -> None:
    payload = run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["scores"]["distribution_adapter"] == 1
    assert payload["data"]["scores"]["claims"] == 1
    assert payload["data"]["scores"]["docs"] == 1
    assert payload["data"]["scores"]["assistant_projection"] == 1
    assert payload["data"]["scores"]["openspec"] == 1
    assert payload["data"]["scores"]["playbooks"] == 1
    assert payload["data"]["scores"]["adoption_scaffold"] == 1
    assert payload["data"]["scores"]["parity_ledger"] == 1
    scorecards = {item["id"]: item for item in payload["data"]["scorecards"]}
    assert scorecards["skills-v2"]["ok"] is True
    assert scorecards["skills-v2"]["mode"] == "v2-strict"
    assert scorecards["skills-v2"]["score"] == scorecards["skills-v2"]["max_score"]
    assert payload["data"]["parity"]["ledger"]["summary"]["unclassified_count"] == 0
    assert payload["data"]["parity"]["gaps"]["ok"] is True
    assert payload["data"]["parity"]["gaps"]["required_gaps"] == []
    assert payload["summary"]["parity_pending_count"] == len(
        payload["data"]["parity"]["gaps"]["required_gaps"]
    )
    assert payload["summary"]["parity_pending_count"] == 0
    assert payload["data"]["parity"]["gaps"]["pending_packages"] == []
    assert payload["summary"]["governance_gap_count"] == 0
    advisory_layer = payload["data"]["gap_layers"]["advisory_signals"]
    assert advisory_layer["blocking"] is False
    assert advisory_layer["gap_count"] == payload["summary"]["advisory_gap_count"]
    assert advisory_layer["advisory_gaps"] == payload["data"]["advisory_signals"]["advisory_gaps"]
    assert advisory_layer["next_actions"] == payload["data"]["advisory_signals"]["next_actions"]
    assert "self_audit" not in payload["data"]
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["data"]["gap_layers"]["governance_audit"] == {
        "scope": "governance_audit",
        "blocking": True,
        "ok": True,
        "required_gaps": [],
        "gap_count": 0,
        "invalid_states": {"categories": {}, "category_count": 0, "gap_count": 0},
    }
    assert payload["data"]["gap_layers"]["capability_parity"] == {
        "scope": "capability_parity",
        "blocking": False,
        "ok": True,
        "required_gaps": payload["data"]["parity"]["gaps"]["required_gaps"],
        "gap_count": payload["summary"]["parity_pending_count"],
        "invalid_states": {"categories": {}, "category_count": 0, "gap_count": 0},
    }
    assert payload["data"]["invalid_states"] == {
        "categories": {},
        "category_count": 0,
        "gap_count": 0,
    }
    parity_note = payload["data"]["parity"]["scope"]["note"].lower()
    assert "raw/cache" not in parity_note
    assert "backend retirement" not in parity_note
    assert "domain profile parity" in parity_note
    assert payload["next_actions"] == ["ethos prove --full"]


def test_shadow_parity_evidence_page_records_accepted_classification() -> None:
    path = Path("evidence/chronicle/shadow-parity-accepted-classification/2026-07-01.md")

    text = path.read_text(encoding="utf-8")

    assert "subject: ethos:evidence:shadow-parity-accepted-classification" in text
    assert "accepted_differences" in text
    assert "external_product_repository_audit_gap" in text
    assert "changed_route_noop" in text
    assert "report_parity_evidence_refresh_bootstrap" in text
    assert "legacy_changed_route_noop" not in text
    assert "shadow_parity_digest" in text


def test_capability_parity_ledger_documents_shadow_evidence_provenance() -> None:
    text = Path("docs/governance/capability-parity-ledger.md").read_text(encoding="utf-8")

    assert "shadow parity evidence freshness" in text
    assert "target_head" in text
    assert "command_sha256" in text
    assert "tracked_evidence" in text
    assert "planned_shadow_run" in text


def test_retired_self_command_group_is_not_available() -> None:
    completed = run_ethos_raw("self", "audit", "--mode", "shape", "--json")

    assert completed.returncode != 0
    assert 'Unknown command "self"' in (completed.stderr or completed.stdout)


def test_quality_types_enforces_ty_policy_tiers() -> None:
    import json as _json

    completed = run_ethos_raw("quality", "types", "--json")
    payload = _json.loads(completed.stdout)

    assert payload["command"] == "quality types"
    packages = payload["data"]["packages"]
    # Zero-tolerance tier packages must report a zero limit; ratchet tiers a baseline.
    # ethos-core absorbs the former ethos-contracts and ethos-quality zero-tolerance
    # packages; ethos remains the ratchet-tier runtime.
    assert packages["packages/ethos-core"]["limit"] == 0
    assert packages["packages/ethos-core"]["tier"] == "zero_tolerance"
    assert packages["packages/ethos"]["tier"] == "ratchet"
    assert packages["packages/ethos"]["limit"] == 75
    assert packages["packages/ethos"]["count"] <= packages["packages/ethos"]["limit"]
    # The gate binds its verdict to exit status (fail-closed): a breach exits non-zero.
    assert completed.returncode == (0 if payload["ok"] else 1)
