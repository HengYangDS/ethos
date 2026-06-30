from __future__ import annotations

import subprocess
from pathlib import Path

from ethos_adapters.shadow import _run_embedded, _run_external, _semantic_diff

from tests.support.ethos_cli_runner import run_ethos


def test_parity_ledger_has_no_unclassified_capabilities() -> None:
    payload = run_ethos("parity", "ledger", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "parity ledger"
    assert payload["summary"]["unclassified_count"] == 0
    assert {record["capability"] for record in payload["data"]["records"]} >= {
        "work-lane-lifecycle",
        "proof-evidence-chronicle",
        "campaign-hypothesis-evolution",
        "assistant-playbooks-skills",
        "quality-determinism-local-state",
        "openspec-claims-trust-review",
        "dmgr-domain-contract-profile",
    }


def test_parity_gaps_reports_alphasim_dmgr_shadow_gap() -> None:
    payload = run_ethos("parity", "gaps", "--adopter", "alphasim-dmgr", "--json")

    assert payload["ok"] is False
    assert payload["command"] == "parity gaps"
    assert "shadow_parity_pending:alphasim-dmgr" in payload["required_gaps"]
    assert len(payload["data"]["pending_packages"]) == len(payload["required_gaps"])


def test_parity_gaps_exposes_concrete_backlog_packages() -> None:
    payload = run_ethos("parity", "gaps", "--json")

    package = payload["data"]["pending_packages"][0]
    assert package["gap"] == "parity_pending:work-lane-lifecycle"
    assert package["capability"] == "work-lane-lifecycle"
    assert package["target_home"] == "ethos-repository + ethos-adapters + ethos-test"
    assert package["required_tests"] == [
        "status/lane/prewrite golden JSON",
        "start lease and execution registry",
        "handoff and closeout dry-run/apply admission",
        "candidate lock and stale-base rejection",
        "foreign lane observe-only protection",
    ]
    assert package["parity_criterion"]
    assert package["rollback_impact"]


def test_parity_shadow_defaults_to_read_only_plan(tmp_path) -> None:
    payload = run_ethos("parity", "shadow", "--target", str(tmp_path), "--json")

    assert payload["ok"] is False
    assert payload["command"] == "parity shadow"
    assert payload["state"] == "planned"
    assert payload["data"]["comparisons"]
    assert payload["data"]["execution_packages"] == [
        {
            "gap": f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}",
            "state": "planned",
            "target": tmp_path.resolve().as_posix(),
            "commands": payload["data"]["comparisons"],
            "semantic_dimensions": payload["data"]["semantic_dimensions"],
            "blocking": True,
            "next_action": (
                f"ethos parity shadow --target {tmp_path.resolve().as_posix()} --execute"
            ),
        }
    ]


def test_parity_shadow_execute_reports_missing_embedded_backend(tmp_path) -> None:
    payload = run_ethos(
        "parity",
        "shadow",
        "--target",
        str(tmp_path),
        "--execute",
        "--timeout-seconds",
        "5",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "different"
    assert any(gap.startswith("embedded_command_failed:") for gap in payload["required_gaps"])
    assert {package["gap"] for package in payload["data"]["execution_packages"]} == set(
        payload["required_gaps"]
    )


def test_embedded_shadow_runner_accepts_pixi_pyproject_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "adopter"
    target.mkdir()
    (target / "pyproject.toml").write_text(
        """
[tool.pixi.workspace]
channels = ["conda-forge"]
platforms = ["osx-arm64"]
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = _run_embedded(target, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["json"]["ok"] is True
    assert calls == [(["pixi", "run", "ethos", "status", "--json"], target.resolve())]


def test_external_shadow_runner_uses_cwd_for_commands_without_root_option(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "assistants doctor"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_external(tmp_path, ("assistants", "doctor"), timeout_seconds=5)

    assert calls[0][0][-3:] == ["assistants", "doctor", "--json"]
    assert "--root" not in calls[0][0]
    assert calls[0][1] == tmp_path.resolve()


def test_external_shadow_runner_uses_root_option_for_rooted_commands(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        text: bool,
        capture_output: bool,
        check: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_external(tmp_path, ("status",), timeout_seconds=5)

    assert calls[0][0][-3:] == ["--root", tmp_path.resolve().as_posix(), "--json"]
    assert calls[0][1] != tmp_path.resolve()


def test_shadow_semantic_diff_derives_state_for_legacy_status_payload() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root"},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "summary": {"dirty": False},
        "required_gaps": [],
        "role": "accepted_root",
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_plan_payload() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "summary": {"changed_path_count": 0},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_assistants_doctor_payload() -> None:
    external = {
        "ok": True,
        "command": "assistants doctor",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "assistants doctor",
        "summary": {"surface_count": 4},
        "required_gaps": [],
    }

    assert _semantic_diff(external, embedded) == {}
