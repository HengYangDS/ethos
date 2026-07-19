from __future__ import annotations

import builtins
import json
import re
from pathlib import Path

import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.repo.status.core as status_core
import ethos.surface.cli.root.planning as planning_cli
from ethos.repository.adoption.planner import adoption_plan
from ethos.surface.cli._base import emit
from ethos_core.contracts.package.ontology import package_ontology_report
from ethos_core.result import EthosResult
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw


def test_status_json_contract() -> None:
    payload = run_ethos("status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "status"
    assert payload["state"] in {"ready", "dirty"}
    assert payload["next_actions"]


def test_status_compact_json_is_bounded_without_foreign_lane_inventory() -> None:
    payload = run_ethos("status", "--json", "--compact")

    assert payload["summary"]["compact"] is True
    assert set(payload["data"]) == {
        "compact",
        "root",
        "branch",
        "head",
        "role",
        "dirty",
        "changed_path_count",
        "landing_readiness",
        "candidate",
        "coordination",
        "stage_gates",
    }
    assert payload["data"]["compact"] is True
    assert isinstance(payload["data"]["changed_path_count"], int)
    assert isinstance(payload["data"]["coordination"]["foreign_work_lane_count"], int)
    assert isinstance(payload["data"]["coordination"]["advisory_count"], int)
    assert "foreign_work_lanes" not in payload["data"]
    assert "branch_bindings" not in payload["data"]


PRIMARY_COMMANDS_WITH_GOVERNANCE_CONTEXT = (
    ("status", "--json"),
    ("plan", "--changed", "--json"),
    ("prove", "--json"),
    ("land", "--json"),
    ("publish", "--json"),
    ("orient", "--json"),
    ("report", "--json"),
)


def _assert_governed_repository_context(context: dict[str, object], *, profile: str) -> None:
    assert context["contract"] == "governed_repository"
    assert context["profile"] == profile
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
    assert context["shared_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert context["transition_commands"] == context["shared_commands"]
    assert context["reader_view_commands"] == ["ethos orient"]
    assert context["scorecard_commands"] == ["ethos report"]
    assert context["truth_boundary"] == "repository"
    assert context["profile_boundary"] == "profile_or_adapter"
    assert context["subject"]["kind"] == "repository"
    assert "posture" not in context


def test_primary_commands_expose_top_level_governance_context(monkeypatch) -> None:
    monkeypatch.setattr(status_core, "_foreign_work_lanes", lambda *_args, **_kwargs: [])

    for command in PRIMARY_COMMANDS_WITH_GOVERNANCE_CONTEXT:
        payload = run_ethos(*command)

        assert "governance_context" in payload, command
        _assert_governed_repository_context(payload["governance_context"], profile="product")

    status_payload = run_ethos("status", "--json")
    assert "governance_context" not in status_payload["data"]


def test_primary_commands_use_same_context_for_adopted_repository(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adoption_plan(repo, profile="generic", apply=True)

    for command in PRIMARY_COMMANDS_WITH_GOVERNANCE_CONTEXT:
        runner = run_ethos_blocked if command[0] == "prove" else run_ethos
        payload = runner(*command[:-1], "--root", repo.as_posix(), command[-1])

        context = payload["governance_context"]
        _assert_governed_repository_context(context, profile="generic")
        assert context["subject"]["id"] == str(repo.resolve())

    status_payload = run_ethos("status", "--root", repo.as_posix(), "--json")
    assert "governance_context" not in status_payload["data"]


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
    assert {
        "python-code",
        "markdown-docs",
        "shell-scripts",
        "toml-config",
    } <= asset_classes


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
    assert adapters["python_format_lint"]["standard"] == "ruff"
    assert adapters["links"]["standard"] == "lychee"
    assert adapters["shell"]["standard"] == "shellcheck"
    assert adapters["toml"]["standard"] == "taplo"
    assert adapters["python_docstrings"]["standard"] == "ethos-docstrings-google"
    assert adapters["python_module_layout"]["standard"] == "ethos-module-layout"


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
    def closed_pipe(*args, **kwargs) -> None:
        raise BrokenPipeError

    monkeypatch.setattr(builtins, "print", closed_pipe)

    emit(EthosResult(command="status", ok=True, state="ready"), json_output=True)


def test_emit_handles_nonblocking_closed_pipes(monkeypatch) -> None:
    def closed_nonblocking_pipe(*args, **kwargs) -> None:
        raise BlockingIOError

    monkeypatch.setattr(builtins, "print", closed_nonblocking_pipe)

    emit(EthosResult(command="publish", ok=True, state="ready"), json_output=True)


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
    assert payload["data"]["workflow_runtime"]["kind"] == "workflow_runtime_read_model"
    assert payload["data"]["workflow_runtime"]["truth_boundary"] == "derived_repository_projection"


def test_plan_changed_surfaces_active_archive_preflight_gap(monkeypatch) -> None:
    lifecycle = {
        "ok": False,
        "required_gaps": [
            "openspec_archive_preflight_failed:sample-change:archive_spec_update_failed"
        ],
    }
    monkeypatch.setattr(
        planning_cli,
        "openspec_governance_report",
        lambda _root, **_kwargs: lifecycle,
        raising=False,
    )

    payload = run_ethos("plan", "--changed", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert payload["required_gaps"] == lifecycle["required_gaps"]
    assert payload["data"]["openspec_lifecycle"] == lifecycle


def test_plan_adopter_surfaces_openspec_lifecycle_gap(monkeypatch, tmp_path: Path) -> None:
    """An adopter plan cannot omit the shared Change lifecycle."""
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, profile="generic", apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")
    lifecycle_payload = {
        "ok": False,
        "required_gaps": ["openspec_claim_binding_missing:material-change"],
    }
    calls: list[tuple[Path, bool, tuple[str, ...]]] = []

    def report(
        root: Path, *, lifecycle: bool = False, changed_paths: tuple[str, ...] = ()
    ) -> dict[str, object]:
        calls.append((root, lifecycle, changed_paths))
        return lifecycle_payload

    monkeypatch.setattr(planning_cli, "openspec_governance_report", report)

    payload = run_ethos("plan", "--changed", "--root", repo.as_posix(), "--json")

    assert calls == [(repo, True, ())]
    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert payload["required_gaps"] == lifecycle_payload["required_gaps"]
    assert (
        payload["data"]["openspec_lifecycle"]["required_gaps"] == lifecycle_payload["required_gaps"]
    )


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
id = "reference"
policy = "rules/reference/contracts.toml"

[[rule]]
id = "reference-cache"
risk = "raw-cache-contract"
paths = ["packages/reference-cache/**"]
requires = ["raw_changed"]
evidence = ["cache-tree"]
""".lstrip(),
        encoding="utf-8",
    )
    contracts = repo / "rules" / "reference" / "contracts.toml"
    contracts.parent.mkdir(parents=True)
    contracts.write_text(
        """
[[contract]]
id = "cache-shape-metadata-sidecars-checkpoint"
surface = "cache"
paths = ["packages/reference-cache/**"]
protects = ["NIO cache shape"]
required_evidence = ["cache-tree"]
""".lstrip(),
        encoding="utf-8",
    )
    source = repo / "packages" / "reference-cache" / "src" / "reference_cache" / "__init__.py"
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

    assert payload["data"]["matched_rules"][0]["id"] == "reference-cache"
    assert payload["data"]["domain_contracts"] == [
        {
            "profile": "reference",
            "contract": "cache-shape-metadata-sidecars-checkpoint",
            "surface": "cache",
            "matched_paths": ["packages/reference-cache/src/reference_cache/__init__.py"],
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
        "source-budget",
        "command-examples",
        "command-registry",
        "command-surface",
        "commits",
        "coupling-audit",
        "coverage",
        "contributor-policy",
        "docs",
        "docs-registry",
        "docs-topology",
        "docstrings",
        "enterprise-readiness",
        "evidence-freshness",
        "format-policy",
        "generated-artifacts",
        "gates",
        "governance-kernel",
        "markdown-links",
        "module-layout",
        "no-compat",
        "npm",
        "package-ontology",
        "product-boundary",
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
            message = f"unexpected OpenSpec command: {args}"
            raise AssertionError(message)
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
    assert payload["data"]["official_cli"]["package"] == "@fission-ai/openspec@1.6.0"
    assert payload["data"]["schema_name"] == "spec-driven"
    assert payload["data"]["commands"]["validate"]["json"]["summary"]["totals"]["failed"] == 0


def test_openspec_lifecycle_flag_reports_lifecycle_summary(monkeypatch) -> None:
    def fake_report(root: Path, *, change: str | None = None, lifecycle: bool = False):
        return {
            "ok": True,
            "official_cli": {
                "package": "@fission-ai/openspec@1.6.0",
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
