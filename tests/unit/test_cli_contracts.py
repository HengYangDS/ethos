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


def test_quality_determinism_commands_are_available() -> None:
    for command in (
        ("quality", "command-surface", "--json"),
        ("quality", "format-policy", "--json"),
        ("quality", "projection-drift", "--json"),
        ("quality", "evidence-freshness", "--json"),
    ):
        payload = run_ethos(*command)
        assert payload["ok"] is True
        assert payload["required_gaps"] == []


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
