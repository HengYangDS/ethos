from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.shadow.core as shadow_core
import ethos.adapters.shadow.execution as shadow_execution
from ethos.adapters.shadow.execution import run_embedded
from ethos.adapters.shadow.execution import run_external
from ethos.repository.evidence.parity.validation import SHADOW_COMMAND_ARGS
from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    import pytest


def test_local_shadow_commands_exclude_remote_publication_probe() -> None:
    """Publication remains public, but local parity must not execute its remote probe."""
    assert ("land",) in SHADOW_COMMAND_ARGS
    assert ("quality", "command-surface") in SHADOW_COMMAND_ARGS
    assert ("publish",) not in SHADOW_COMMAND_ARGS


def test_parity_shadow_defaults_to_read_only_plan(tmp_path: Path) -> None:
    payload = run_ethos("parity", "shadow", "--target", str(tmp_path), "--json")
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path.cwd(),
        text=True,
        check=True,
        capture_output=True,
    ).stdout.strip()

    assert payload["ok"] is False
    assert payload["command"] == "parity shadow"
    assert payload["state"] == "planned"
    assert "ethos quality command-surface --json" in payload["data"]["comparisons"]
    assert payload["data"]["execution_packages"] == [
        {
            "gap": f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}",
            "state": "planned",
            "target": tmp_path.resolve().as_posix(),
            "commands": payload["data"]["comparisons"],
            "semantic_dimensions": payload["data"]["semantic_dimensions"],
            "blocking": True,
            "provenance": {
                "mode": "planned_shadow_run",
                "evidence_path": "",
                "freshness": {
                    "ok": False,
                    "required_gaps": [
                        f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}"
                    ],
                    "product_head": "",
                    "current_product_head": current_head,
                    "target_head": "",
                    "current_target_head": "",
                    "command_sha256": "",
                },
            },
            "refresh_package": {
                "kind": "parity_evidence_refresh",
                "adopter": "generic",
                "root": Path.cwd().resolve().as_posix(),
                "target": tmp_path.resolve().as_posix(),
                "blocking": True,
                "required_gaps": [f"shadow_parity_not_executed:{tmp_path.resolve().as_posix()}"],
                "lifecycle": {
                    "stage": "work_lane_before_proof",
                    "write_root": Path.cwd().resolve().as_posix(),
                    "write_path": "evidence/parity/generic-shadow.json",
                    "commit_before_proof": True,
                    "authority_boundary": (
                        "refresh and commit tracked parity evidence from the admitted "
                        "Work Lane; candidate and accepted roots remain write-protected"
                    ),
                },
                "command": (
                    "ethos parity shadow --adopter generic "
                    f"--target {tmp_path.resolve().as_posix()} "
                    "--execute --write-evidence --json"
                ),
                "next_action": "refresh and commit tracked shadow parity evidence before proof",
            },
            "next_action": (
                "ethos parity shadow --adopter generic "
                f"--target {tmp_path.resolve().as_posix()} "
                "--execute --write-evidence --json"
            ),
        }
    ]


def test_parity_shadow_execute_reports_missing_embedded_backend(tmp_path: Path) -> None:
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
    embedded = payload["data"]["comparisons"][0]["embedded"]
    assert embedded["backend"] == {
        "kind": "missing",
        "command": "",
        "blocking": True,
        "required_gaps": ["embedded_backend_missing"],
    }
    assert "embedded_backend_missing" in payload["required_gaps"]
    assert any(gap.startswith("embedded_command_failed:") for gap in payload["required_gaps"])
    assert {package["gap"] for package in payload["data"]["execution_packages"]} == set(
        payload["required_gaps"]
    )


def test_shadow_json_runner_normalizes_timeout_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = ["ethos", "status", "--json"]

    def timeout(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            command,
            timeout=1,
            output=b'{"partial":true}',
            stderr=b"timed out",
        )

    monkeypatch.setattr(subprocess, "run", timeout)

    result = shadow_execution.run_json_command(command, cwd=tmp_path, timeout_seconds=1)

    assert result == {
        "exit_code": 124,
        "stdout": '{"partial":true}',
        "stderr": "timed out",
        "json": {},
    }


def test_embedded_shadow_runner_accepts_pixi_pyproject_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_embedded(target, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["json"]["ok"] is True
    assert result["backend"] == {
        "kind": "pixi",
        "command": "pixi run ethos status --json",
        "blocking": False,
        "required_gaps": [],
    }
    assert calls == [(["pixi", "run", "ethos", "status", "--json"], target.resolve())]


def test_shadow_embedded_runner_accepts_pixi_task_in_pyproject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        """
[tool.pixi.tasks]
ethos = "python -m ethos.cli"
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_embedded(repo, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["backend"] == {
        "kind": "pixi",
        "command": "pixi run ethos status --json",
        "blocking": False,
        "required_gaps": [],
    }
    assert calls == [(["pixi", "run", "ethos", "status", "--json"], repo.resolve())]


def test_shadow_embedded_runner_accepts_uv_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        """
[tool.uv.workspace]
members = ["packages/ethos"]
""".lstrip(),
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status", "state": "ready"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_embedded(repo, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["json"]["ok"] is True
    assert result["backend"] == {
        "kind": "uv-workspace",
        "command": "uv run --package ethos ethos status --json",
        "blocking": False,
        "required_gaps": [],
    }
    assert calls == [
        (
            ["uv", "run", "--package", "ethos", "ethos", "status", "--json"],
            repo.resolve(),
        )
    ]


def test_external_shadow_runner_uses_cwd_for_commands_without_root_option(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "assistants doctor"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_external(tmp_path, ("assistants", "doctor"), timeout_seconds=5)

    assert calls[0][0][-3:] == ["assistants", "doctor", "--json"]
    assert "--root" not in calls[0][0]
    assert calls[0][1] == tmp_path.resolve()


def test_external_shadow_runner_uses_root_option_for_rooted_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"ok": true, "command": "status"}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_external(tmp_path, ("status",), timeout_seconds=5)

    assert calls[0][0][-3:] == ["--root", tmp_path.resolve().as_posix(), "--json"]
    assert calls[0][1] != tmp_path.resolve()


def test_shadow_json_verdict_exit_code_one_is_not_infrastructure_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pixi.toml").write_text("", encoding="utf-8")
    payload = {
        "ok": False,
        "command": "status",
        "state": "blocked",
        "required_gaps": ["x"],
    }

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(shadow_core, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(subprocess, "run", fake_run)

    report = shadow_core.run_shadow_parity(repo, timeout_seconds=5)

    assert report["ok"] is True
    assert not any(gap.startswith("external_command_failed:") for gap in report["required_gaps"])
    assert not any(gap.startswith("embedded_command_failed:") for gap in report["required_gaps"])


def test_shadow_malformed_json_payload_is_process_failure() -> None:
    assert shadow_execution.process_failed(
        {
            "exit_code": 0,
            "stdout": '{"error": "boom"}',
            "stderr": "",
            "json": {"error": "boom"},
        }
    )


def test_shadow_exit_code_above_one_is_process_failure_even_with_verdict() -> None:
    assert shadow_execution.process_failed(
        {
            "exit_code": 2,
            "stdout": '{"ok": false, "command": "status", "required_gaps": []}',
            "stderr": "",
            "json": {"ok": False, "command": "status", "required_gaps": []},
        }
    )


def test_shadow_json_runner_isolates_timeout_process_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(
            {
                "command": command,
                "cwd": kwargs["cwd"],
                "text": kwargs["text"],
                "capture_output": kwargs["capture_output"],
                "check": kwargs["check"],
                "timeout": kwargs["timeout"],
                "start_new_session": kwargs["start_new_session"],
            }
        )
        raise subprocess.TimeoutExpired(
            command,
            kwargs["timeout"],
            output="partial",
            stderr="late",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = shadow_execution.run_json_command(
        ["ethos", "status", "--json"],
        cwd=tmp_path,
        timeout_seconds=7,
    )

    assert result == {
        "exit_code": 124,
        "stdout": "partial",
        "stderr": "late",
        "json": {},
    }
    assert calls == [
        {
            "command": ["ethos", "status", "--json"],
            "cwd": tmp_path,
            "text": True,
            "capture_output": True,
            "check": False,
            "timeout": 7,
            "start_new_session": True,
        }
    ]
