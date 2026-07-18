from __future__ import annotations

import importlib.util
import json
import stat
import tomllib
from pathlib import Path

from tests.support.architecture import run_json
from tests.support.architecture import tool_block

# fmt: off

ROOT = Path(__file__).resolve().parents[2]
MIN_FORMAT_REGISTRY_ENTRIES = 8
MIN_RUNBOOK_REGISTRY_ENTRIES = 6


def _load_format_selection_module():
    module_path = ROOT / "tools/ci/format_selection.py"
    spec = importlib.util.spec_from_file_location("ethos_test_format_selection", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


format_selection = _load_format_selection_module()


def test_format_selection_config_is_fail_closed_and_executable() -> None:
    config = tomllib.loads((ROOT / ".config/checks/format/selection.toml").read_text())
    formats = config["format"]
    assert len(formats) >= MIN_FORMAT_REGISTRY_ENTRIES
    assert config["policy"]["unregistered_extension"] == "block"
    assert config["policy"]["forbid_tracked_extensions"] == [".pickle", ".pkl", ".joblib"]
    assert any(item["extensions"] == [".c4"] for item in formats)
    assert any(item["extensions"] == [".mmd"] for item in formats)
    assert any(item["extensions"] == [".j2"] for item in formats)

    payload = run_json(ROOT, ["tools/ci/scripts/run-format-selection.sh"])
    assert payload["kind"] == "ethos_format_selection_audit"
    assert payload["ok"] is True
    assert payload["format_count"] >= MIN_FORMAT_REGISTRY_ENTRIES
    assert payload["observed_unregistered_extension_count"] == 0
    assert payload["observed_unregistered_extensions"] == []


def test_format_selection_blocks_an_unregistered_tracked_extension(monkeypatch, capsys) -> None:
    monkeypatch.setattr(format_selection, "_tracked_files", lambda: ["system/new-policy.cue"])
    monkeypatch.setattr(
        format_selection,
        "_load_config",
        lambda: {
            "format": [{"extensions": [".toml"]}],
            "policy": {
                "forbid_tracked_extensions": [],
                "jsonl_allowed_roots": [],
                "yaml_allowed_roots": [],
                "unregistered_extension": "block",
            },
        },
    )

    assert format_selection.main() == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["failures"] == [
        {"path": "system/new-policy.cue", "reason": "unregistered tracked extension: .cue"}
    ]


def test_architecture_projection_is_checked_from_source_to_mermaid() -> None:
    config = tomllib.loads((ROOT / ".config/checks/architecture/projection.toml").read_text())
    projection = config["projection"][0]
    assert projection["source"] == ".config/checks/architecture/models/ethos_repository.c4"
    assert projection["output"] == "docs/architecture/_generated/ethos-repository.mmd"

    payload = run_json(ROOT, ["tools/ci/scripts/run-architecture-projection-drift.sh"])
    assert payload["kind"] == "ethos_architecture_projection_drift"
    assert payload["ok"] is True
    assert payload["projections"][0]["matches"] is True

    generated = (ROOT / projection["output"]).read_text(encoding="utf-8")
    assert "Generated from .config/checks/architecture/models/ethos_repository.c4" in generated
    assert "flowchart LR" in generated
    assert "Provider projections" in generated


def test_runbook_registry_drift_check_covers_new_runbooks() -> None:
    payload = run_json(ROOT, ["tools/ci/scripts/run-runbook-registry-check.sh"])
    assert payload["kind"] == "ethos_runbook_registry_check"
    assert payload["ok"] is True
    assert payload["entry_count"] >= MIN_RUNBOOK_REGISTRY_ENTRIES

    text = (ROOT / "docs/reference/runbook-registry.md").read_text(encoding="utf-8")
    for runbook in [
        "RUN-CI-TEMPLATES",
        "RUN-GITHUB-EMULATOR",
        "RUN-GITLAB-EMULATOR",
        "RUN-FORMAT-SELECTION",
        "RUN-ARCHITECTURE-PROJECTION",
        "RUN-MCP-SMOKE",
        "RUN-DEPENDENCY-HYGIENE",
        "RUN-JSON-SCHEMA",
        "RUN-PROSE-CHECK",
        "RUN-HOSTED-PROVIDER-OBSERVATION",
        "RUN-PYTHON-VULNERABILITY-AUDIT",
    ]:
        assert runbook in text


def test_mcp_smoke_is_projection_only_and_writes_local_evidence() -> None:
    payload = run_json(ROOT, ["tools/ci/scripts/run-mcp-smoke.sh"])
    evidence = ROOT / str(payload["evidence_path"])
    persisted = json.loads(evidence.read_text(encoding="utf-8"))
    latest = ROOT / str(payload["latest_projection_path"])

    assert payload == persisted
    assert latest.is_file()
    assert payload["kind"] == "ethos_mcp_projection_smoke"
    assert payload["ok"] is True
    assert "repository proof" in payload["not_claimed"]
    assert "MCP server semantic correctness" in payload["not_claimed"]


def test_active_p1_p2_tools_have_owner_surfaces() -> None:
    active = {
        "format_selection": "tools/ci/scripts/run-format-selection.sh",
        "architecture_modeling": "tools/ci/scripts/run-architecture-projection-drift.sh",
        "architecture_projection_drift": "tools/ci/scripts/run-architecture-projection-drift.sh",
        "runbook_registry": "tools/ci/scripts/run-runbook-registry-check.sh",
        "mcp_smoke": "tools/ci/scripts/run-mcp-smoke.sh",
    }
    for concern, gate in active.items():
        block = tool_block(ROOT, concern)
        script = ROOT / gate
        assert f'gate = "{gate}"' in block
        assert "planned = true" not in block
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR

    provider_text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    github_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    combined = provider_text + github_text
    for gate in active.values():
        assert gate in combined


def test_optional_adapters_and_supply_chain_remain_planned() -> None:
    for concern in [
        "osv_vuln",
        "signing",
        "nox_runner_adapter",
        "pixi_environment_adapter",
        "pants_graph_adapter",
        "task_ledger_adapter",
        "agent_method_pack_adapter",
    ]:
        block = tool_block(ROOT, concern)
        assert 'adoption = "candidate"' in block

# fmt: on
