from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = os.pathsep.join(
    str(ROOT / package / "src")
    for package in (
        "packages/ethos",
        "packages/ethos-kernel",
        "packages/ethos-governance",
        "packages/ethos-workspace",
        "packages/ethos-agent",
        "packages/ethos-adopt",
    )
)


def run_ethos(*args: str, cwd: Path | None = None) -> dict[str, object]:
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH
    completed = subprocess.run(
        [sys.executable, "-m", "ethos.cli", *args],
        cwd=cwd or ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_status_json_contract() -> None:
    payload = run_ethos("status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "status"
    assert payload["state"] in {"ready", "dirty"}
    assert payload["next_actions"]


def test_plan_changed_returns_action_graph() -> None:
    payload = run_ethos("plan", "--changed", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "plan"
    assert "action_graph" in payload["data"]


def test_self_audit_reports_product_shape() -> None:
    payload = run_ethos("self", "audit", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "self audit"
    assert payload["required_gaps"] == []
    assert payload["data"]["package_ontology"]["ok"] is True


def test_adopt_dry_run_does_not_write_project(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    payload = run_ethos("adopt", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "adopt"
    assert ".ethos/project.toml" in payload["data"]["planned_files"]
    assert not (tmp_path / ".ethos").exists()


def test_quality_command_registry_rejects_retired_public_roots() -> None:
    payload = run_ethos("quality", "command-registry", "--json")

    assert payload["ok"] is True
    assert payload["data"]["retired_public_roots"] == []
    assert "ethos status" in payload["data"]["public_commands"]


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
        ("quality", "commits", "--json"),
        ("quality", "release", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_prove_execute_can_select_real_gates() -> None:
    payload = run_ethos(
        "prove",
        "--execute",
        "--gate",
        "self-audit",
        "--gate",
        "claims",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["summary"]["gate_count"] == 2
    assert {run["state"] for run in payload["data"]["evidence"]["runs"]} == {"passed"}


def test_adopt_gitlab_profile_is_available(tmp_path: Path) -> None:
    payload = run_ethos(
        "adopt",
        "--root",
        str(tmp_path),
        "--profile",
        "gitlab",
        "--dry-run",
        "--json",
    )

    assert payload["ok"] is True
    assert payload["data"]["profile"] == "gitlab"
    assert ".gitlab-ci.yml" in payload["data"]["planned_files"]


def test_assistant_mcp_server_command_is_available() -> None:
    payload = run_ethos("assistants", "mcp-server", "--json")

    assert payload["ok"] is True
    assert payload["data"]["server"]["protocol"] == "mcp"


def test_quality_determinism_commands_are_available() -> None:
    for command in (
        ("quality", "command-surface", "--json"),
        ("quality", "format-policy", "--json"),
        ("quality", "projection-drift", "--json"),
        ("quality", "evidence-freshness", "--json"),
        ("quality", "command-examples", "--json"),
        ("quality", "docs-registry", "--json"),
        ("quality", "provenance", "--json"),
        ("quality", "claims", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


def test_prove_returns_evidence_and_provenance() -> None:
    payload = run_ethos("prove", "--objective", "cli contract", "--json")

    assert payload["ok"] is True
    assert payload["data"]["evidence"]["digest"]
    assert payload["data"]["provenance"]["subject"][0]["digest"]["sha256"] == (
        payload["data"]["evidence"]["digest"]
    )


def test_land_apply_requires_authorization_and_expected_head() -> None:
    payload = run_ethos("land", "--apply", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


def test_publish_apply_requires_authorization_and_expected_head() -> None:
    payload = run_ethos("publish", "--apply", "--json")

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


def test_assistant_projection_commands_are_available() -> None:
    manifest = run_ethos("assistants", "mcp-manifest", "--json")
    projections = run_ethos("assistants", "check-projections", "--json")
    doctor = run_ethos("assistants", "doctor", "--json")

    assert manifest["ok"] is True
    assert "ethos.status" in manifest["data"]["manifest"]["tools"]
    assert projections["ok"] is True
    assert projections["data"]["contract"]["truth"] == "ethos-kernel-and-repository"
    assert doctor["ok"] is True


def test_campaign_hypotheses_are_visible() -> None:
    payload = run_ethos("campaign", "hypotheses", "--json")

    assert payload["ok"] is True
    assert payload["data"]["hypotheses"]


def test_docs_command_uses_registry_for_discovery() -> None:
    payload = run_ethos("docs", "agent-projections", "--json")

    assert payload["ok"] is True
    assert payload["data"]["path"] == "docs/architecture/agent-projections.md"


def test_report_scorecard_is_derived_from_governance_checks() -> None:
    payload = run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["scores"]["claims"] == 1
    assert payload["data"]["scores"]["docs"] == 1
    assert payload["data"]["scores"]["assistant_projection"] == 1


def test_self_evolution_loop_commands_are_available() -> None:
    for command in (
        ("self", "observe", "--json"),
        ("self", "hypothesize", "--json"),
        ("self", "experiment", "--json"),
        ("self", "prove", "--json"),
        ("self", "canonize", "--json"),
        ("self", "retire", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["command"].startswith("self ")


def test_init_command_is_adoption_alias_without_writing(tmp_path: Path) -> None:
    payload = run_ethos("init", "--root", str(tmp_path), "--dry-run", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "init"
    assert not (tmp_path / ".ethos").exists()
