from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.shadow.core as shadow_core
import ethos.adapters.shadow.execution as shadow_execution
from ethos.adapters.shadow.core import run_shadow_parity
from ethos.adapters.shadow.semantics import accepted_semantic_differences
from ethos.repository.policy.schema import validate_schema_instance
from tests.unit.product.parity.snapshots import git_head
from tests.unit.product.parity.snapshots import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_shadow_accepted_difference_exposes_counts_and_command_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_external(
        target: Path,
        command: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        _ = (target, timeout_seconds)
        command_name = command[0] if command[0] != "assistants" else "assistants doctor"
        if command[:2] == ("quality", "command-surface"):
            command_name = "quality command-surface"
        if command[0] == "playbooks":
            command_name = "playbooks route"
        if command == ("prove",):
            payload = {
                "ok": False,
                "command": "prove",
                "state": "gapped",
                "required_gaps": ["claims_missing"],
                "data": {"repository_audit": {"required_gaps": ["claims_missing"]}},
            }
        else:
            state_by_command = {
                "status": "ready",
                "plan": "planned",
                "report": "ready",
                "quality command-surface": "clean",
                "assistants doctor": "ready",
                "playbooks route": "routed",
                "land": "ready_to_land",
                "publish": "local_publish_ready",
            }
            payload = {
                "ok": True,
                "command": command_name,
                "state": state_by_command[command_name],
                "required_gaps": [],
            }
        return {"exit_code": 0, "stdout": "", "stderr": "", "json": payload}

    def fake_embedded(
        target: Path,
        command: tuple[str, ...],
        *,
        timeout_seconds: int,
    ) -> dict[str, object]:
        _ = (target, timeout_seconds)
        command_name = command[0] if command[0] != "assistants" else "assistants doctor"
        if command[:2] == ("quality", "command-surface"):
            command_name = "quality command-surface"
        if command[0] == "playbooks":
            command_name = "playbooks route"
        state_by_command = {
            "status": "ready",
            "plan": "planned",
            "prove": "proven",
            "report": "ready",
            "quality command-surface": "clean",
            "assistants doctor": "ready",
            "playbooks route": "routed",
            "land": "ready_to_land",
            "publish": "local_publish_ready",
        }
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {
                "ok": True,
                "command": command_name,
                "state": state_by_command[command_name],
                "required_gaps": [],
            },
        }

    monkeypatch.setattr("ethos.adapters.shadow.execution.run_external", fake_external)
    monkeypatch.setattr("ethos.adapters.shadow.execution.run_embedded", fake_embedded)

    payload = run_shadow_parity(tmp_path, timeout_seconds=5)

    assert payload["ok"] is True
    assert payload["accepted_summary"] == {
        "total_count": 1,
        "command_count": 1,
        "kind_counts": {"external_product_repository_audit_gap": 1},
    }
    comparison = next(item for item in payload["comparisons"] if item["command"] == "ethos prove")
    assert comparison["accepted_summary"] == {
        "total_count": 1,
        "kind_counts": {"external_product_repository_audit_gap": 1},
    }
    assert comparison["accepted_differences"] == [
        {
            "kind": "external_product_repository_audit_gap",
            "classification": "accepted",
            "scope": "external_product_repository_audit",
            "commands": ["ethos prove"],
            "gaps": ["claims_missing"],
            "reason": "external product repository audit gap is not an embedded adopter parity gap",
        }
    ]

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_parity_report_includes_identity_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    (repo / ".ethos").mkdir()
    (repo / ".ethos" / "profile.toml").write_text(
        'schema_version = 1\nprofile_id = "sample"\n[roots]\nrules = "rules"\n',
        encoding="utf-8",
    )
    (repo / "rules").mkdir()
    (repo / "rules" / "contracts.toml").write_text('kind = "rules"\n', encoding="utf-8")

    def fake_external(
        target: Path, command: tuple[str, ...], *, timeout_seconds: int
    ) -> dict[str, object]:
        _ = (target, timeout_seconds)
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {"ok": True, "command": command[0], "state": "ready", "required_gaps": []},
        }

    def fake_embedded(
        target: Path, command: tuple[str, ...], *, timeout_seconds: int
    ) -> dict[str, object]:
        _ = (target, timeout_seconds)
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {"ok": True, "command": command[0], "state": "ready", "required_gaps": []},
            "backend": {
                "kind": "pixi",
                "command": "pixi run ethos status --json",
                "blocking": False,
                "required_gaps": [],
            },
            "required_gaps": [],
        }

    monkeypatch.setattr(shadow_core, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(shadow_execution, "run_external", fake_external)
    monkeypatch.setattr(shadow_execution, "run_embedded", fake_embedded)

    payload = run_shadow_parity(repo, timeout_seconds=5)

    identity = payload["identity"]
    assert identity["target_root"] == repo.resolve().as_posix()
    assert identity["target_head"] == git_head(repo)
    assert identity["changed_paths"] == [".ethos/profile.toml", "rules/contracts.toml"]
    assert identity["commands"] == ["ethos status --json"]
    assert identity["external_commands"][0].endswith(
        "ethos.cli status --root " + repo.resolve().as_posix() + " --json"
    )
    assert identity["embedded_commands"] == ["pixi run ethos status --json"]
    assert {item["path"] for item in identity["evidence_inputs"]} >= {
        ".ethos/profile.toml",
        "rules",
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_accepted_difference_schema_rejects_unknown_kind() -> None:
    payload = {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"unknown": 1},
        },
        "false_negative_count": 0,
        "comparisons": [
            {
                "command": "ethos prove",
                "external": {"exit_code": 0, "stdout": "", "stderr": "", "json": {}},
                "embedded": {"exit_code": 0, "stdout": "", "stderr": "", "json": {}},
                "semantic_diff": {},
                "false_negative_gaps": [],
                "accepted_summary": {"total_count": 1, "kind_counts": {"unknown": 1}},
                "accepted_differences": [
                    {
                        "kind": "unknown",
                        "classification": "accepted",
                        "scope": "external_product_repository_audit",
                        "commands": ["ethos prove"],
                        "gaps": ["claims_missing"],
                        "reason": "invalid",
                    }
                ],
            }
        ],
        "execution_packages": [],
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_shadow_accepted_difference_has_stable_shape() -> None:
    external = {
        "ok": False,
        "command": "prove",
        "state": "gapped",
        "required_gaps": ["claims_missing"],
        "data": {"repository_audit": {"required_gaps": ["claims_missing"]}},
    }
    embedded = {"ok": True, "command": "prove", "required_gaps": []}

    accepted = accepted_semantic_differences(external, embedded)

    assert accepted == [
        {
            "kind": "external_product_repository_audit_gap",
            "classification": "accepted",
            "scope": "external_product_repository_audit",
            "commands": ["ethos prove"],
            "gaps": ["claims_missing"],
            "reason": "external product repository audit gap is not an embedded adopter parity gap",
        }
    ]
