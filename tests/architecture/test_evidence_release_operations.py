from __future__ import annotations

import json
import stat
import tomllib
from pathlib import Path

from tests.support.architecture import run_json
from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]
SHA256_HEX_LENGTH = 64


def test_closeout_manifest_hashes_reviewed_evidence_carriers() -> None:
    config = tomllib.loads((ROOT / ".config/checks/evidence/closeout.toml").read_text())
    assert config["output"] == "build/evidence/workflow/closeout/manifest.json"

    payload = run_json(ROOT, ["tools/ci/scripts/run-closeout-evidence-manifest.sh"])
    persisted = json.loads(
        (ROOT / "build/evidence/workflow/closeout/manifest.json").read_text(encoding="utf-8")
    )

    assert payload == persisted
    assert payload["kind"] == "ethos_closeout_evidence_manifest"
    assert payload["ok"] is True
    topic = payload["topics"][0]
    assert topic["id"] == "tooling-adoption-roadmap"
    assert {item["role"] for item in topic["files"]} == {"claim", "chronicle", "openspec"}
    openspec_file = next(item for item in topic["files"] if item["role"] == "openspec")
    assert (
        openspec_file["path"]
        == "openspec/changes/archive/2026-07-09-complete-planning-closeout/tasks.md"
    )
    assert all(len(item["sha256"]) == SHA256_HEX_LENGTH for item in topic["files"])


def test_local_state_audit_keeps_generated_state_out_of_repository_truth() -> None:
    payload = run_json(ROOT, ["tools/ci/scripts/run-local-state-audit.sh"])
    persisted = json.loads((ROOT / "build/evidence/local-state/audit.json").read_text())

    assert payload == persisted
    assert payload["kind"] == "ethos_local_state_audit"
    assert payload["ok"] is True
    assert payload["forbidden_tracked_state"] == []


def test_release_supply_chain_uses_ethos_native_envelopes_without_publication_claims() -> None:
    payload = run_json(ROOT, ["tools/ci/scripts/run-release-supply-chain.sh"])
    persisted = json.loads((ROOT / "build/evidence/release/supply-chain.json").read_text())

    assert payload == persisted
    assert payload["kind"] == "ethos_release_supply_chain_envelope"
    assert payload["ok"] is True
    assert "remote release published" in payload["not_claimed"]
    assert "hosted CI passed" in payload["not_claimed"]
    commands = {item["command"] for item in payload["commands"]}
    assert "uv run --package ethos ethos quality sbom --json" in commands
    assert "uv run --package ethos ethos quality release-attestation --json" in commands
    assert "uv run --package ethos ethos quality release-policy --json" in commands


def test_evidence_and_release_gates_have_active_owner_surfaces() -> None:
    active = {
        "local_state_audit": "tools/ci/scripts/run-local-state-audit.sh",
        "closeout_evidence_manifest": "tools/ci/scripts/run-closeout-evidence-manifest.sh",
        "sbom": "tools/ci/scripts/run-release-supply-chain.sh",
        "attestation": "tools/ci/scripts/run-release-supply-chain.sh",
    }
    for concern, gate in active.items():
        block = tool_block(ROOT, concern)
        script = ROOT / gate
        assert f'gate = "{gate}"' in block
        assert "planned = true" not in block
        assert script.is_file()
        assert script.stat().st_mode & stat.S_IXUSR

    for concern in ["osv_vuln", "image_package_scan", "signing"]:
        block = tool_block(ROOT, concern)
        assert "planned = true" in block


def test_ci_and_runbook_project_evidence_and_release_gates() -> None:
    combined_ci = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8") + (
        ROOT / ".github/workflows/ci.yml"
    ).read_text(encoding="utf-8")
    runbook = (ROOT / "docs/reference/runbook-registry.md").read_text(encoding="utf-8")
    template_config = (ROOT / ".config/checks/ci/templates.toml").read_text(encoding="utf-8")

    for script in [
        "tools/ci/scripts/run-closeout-evidence-manifest.sh",
        "tools/ci/scripts/run-local-state-audit.sh",
        "tools/ci/scripts/run-release-supply-chain.sh",
    ]:
        assert script in combined_ci
        assert script in runbook
        assert script in template_config
