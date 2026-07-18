from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.shadow.core as shadow_core
import ethos.adapters.shadow.execution as shadow_execution
from ethos.adapters.shadow.execution import run_embedded
from ethos.adapters.shadow.execution import run_external
from ethos.repository.evidence.parity.validation import SHADOW_COMMAND_ARGS
from tests.support.ethos_cli_runner import run_ethos
from tests.unit.product.parity.snapshots import successful_shadow_popen


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

    class TimedOutProcess:
        pid = 4321
        calls = 0

        def communicate(self, timeout: int | None = None):
            _ = timeout
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired(
                    command,
                    timeout=1,
                    output=b'{"partial":true}',
                    stderr=b"timed out",
                )
            return b'{"partial":true}', b"timed out"

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: TimedOutProcess())
    monkeypatch.setattr(os, "killpg", lambda *_args: None)

    result = shadow_execution.run_json_command(command, cwd=tmp_path, timeout_seconds=1)

    assert result == {
        "exit_code": 124,
        "stdout": '{"partial":true}',
        "stderr": "timed out",
        "json": {},
    }


def test_shadow_json_runner_terminates_timed_out_command_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = ["ethos", "status", "--json"]
    killed: list[tuple[int, int]] = []

    class TimedOutProcess:
        pid = 4321
        calls = 0

        def communicate(self, timeout: int | None = None):
            _ = timeout
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired(command, timeout=1)
            return "", ""

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: TimedOutProcess())
    monkeypatch.setattr(os, "killpg", lambda pid, signal: killed.append((pid, signal)))

    result = shadow_execution.run_json_command(command, cwd=tmp_path, timeout_seconds=1)

    assert result["exit_code"] == 124
    assert killed == [(4321, signal.SIGTERM)]


def test_shadow_json_runner_escalates_when_term_grace_expires(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = ["ethos", "status", "--json"]
    killed: list[tuple[int, int]] = []

    class TimedOutProcess:
        pid = 4321
        calls = 0

        def communicate(self, timeout: int | None = None):
            self.calls += 1
            if self.calls <= 2:
                raise subprocess.TimeoutExpired(command, timeout=timeout or 1)
            return "", ""

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: TimedOutProcess())
    monkeypatch.setattr(os, "killpg", lambda pid, signal: killed.append((pid, signal)))

    result = shadow_execution.run_json_command(command, cwd=tmp_path, timeout_seconds=1)

    assert result["exit_code"] == 124
    assert killed == [(4321, signal.SIGTERM), (4321, signal.SIGKILL)]


@pytest.mark.parametrize(
    "helper",
    [
        shadow_execution._terminate_process_group,  # noqa: RUF100, SLF001 - exact cleanup boundary coverage
        shadow_execution._kill_process_group,  # noqa: RUF100, SLF001 - exact cleanup boundary coverage
    ],
)
@pytest.mark.parametrize("error", [ProcessLookupError, PermissionError])
def test_shadow_process_group_cleanup_tolerates_absent_or_forbidden_groups(
    monkeypatch: pytest.MonkeyPatch,
    helper,
    error,
) -> None:
    monkeypatch.setattr(os, "killpg", lambda *_args: (_ for _ in ()).throw(error()))

    helper(0)
    helper(4321)


@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "pixi-workspace",
            "pyproject": '[tool.pixi.workspace]\nchannels = ["conda-forge"]\nplatforms = ["osx-arm64"]\n',
            "backend": {
                "kind": "pixi",
                "command": "pixi run ethos status --json",
                "blocking": False,
                "required_gaps": [],
            },
            "argv": ["pixi", "run", "ethos", "status", "--json"],
        },
        {
            "name": "pixi-task",
            "pyproject": '[tool.pixi.tasks]\nethos = "python -m ethos.cli"\n',
            "backend": {
                "kind": "pixi",
                "command": "pixi run ethos status --json",
                "blocking": False,
                "required_gaps": [],
            },
            "argv": ["pixi", "run", "ethos", "status", "--json"],
        },
        {
            "name": "uv-workspace",
            "pyproject": '[tool.uv.workspace]\nmembers = ["packages/ethos"]\n',
            "backend": {
                "kind": "uv-workspace",
                "command": "uv run --package ethos ethos status --json",
                "blocking": False,
                "required_gaps": [],
            },
            "argv": ["uv", "run", "--package", "ethos", "ethos", "status", "--json"],
        },
    ],
    ids=["pixi-workspace", "pixi-task", "uv-workspace"],
)
def test_embedded_shadow_runner_selects_declared_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, object],
) -> None:
    repo = tmp_path / str(case["name"])
    repo.mkdir()
    (repo / "pyproject.toml").write_text(str(case["pyproject"]), encoding="utf-8")
    calls: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(subprocess, "Popen", successful_shadow_popen(calls))

    result = run_embedded(repo, ("status",), timeout_seconds=5)

    assert result["exit_code"] == 0
    assert result["json"]["ok"] is True
    assert result["backend"] == case["backend"]
    assert calls == [(case["argv"], repo.resolve())]


@pytest.mark.parametrize(
    "case",
    [
        {
            "command": ("assistants", "doctor"),
            "reported": "assistants doctor",
            "suffix": ["assistants", "doctor", "--json"],
            "uses_cwd": True,
        },
        {
            "command": ("status",),
            "reported": "status",
            "suffix": ["--root", "{root}", "--json"],
            "uses_cwd": True,
        },
    ],
    ids=["cwd-command", "rooted-command"],
)
def test_external_shadow_runner_binds_command_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, object],
) -> None:
    calls: list[tuple[list[str], Path]] = []
    monkeypatch.setattr(
        subprocess,
        "Popen",
        successful_shadow_popen(calls, reported_command=str(case["reported"])),
    )

    command = case["command"]
    assert isinstance(command, tuple)
    run_external(tmp_path, command, timeout_seconds=5)

    suffix = case["suffix"]
    assert isinstance(suffix, list)
    expected = [str(part).format(root=tmp_path.resolve().as_posix()) for part in suffix]
    assert calls[0][0][-len(expected) :] == expected
    assert (calls[0][1] == tmp_path.resolve()) is case["uses_cwd"]
    assert calls[0][0][0] == shadow_execution.external_python(tmp_path)


def test_external_shadow_runner_prefers_source_bound_runtime_to_root_dot_venv(
    tmp_path: Path,
) -> None:
    runtime_python = tmp_path / "build/runtime/venv/bin/python"
    runtime_python.parent.mkdir(parents=True)
    runtime_python.touch()
    legacy_python = tmp_path / ".venv/bin/python"
    legacy_python.parent.mkdir(parents=True)
    legacy_python.touch()

    assert shadow_execution.external_python(tmp_path) == runtime_python.as_posix()


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

    class Process:
        returncode = 1

        def communicate(self, timeout: int | None = None) -> tuple[str, str]:
            _ = timeout
            return json.dumps(payload), ""

    original_popen = subprocess.Popen

    def fake_popen(*args: Any, **kwargs: Any) -> Process | subprocess.Popen[str]:
        command = args[0]
        if command[0] == "git":
            return original_popen(*args, **kwargs)
        return Process()

    monkeypatch.setattr(shadow_core, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

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


def test_shadow_json_runner_creates_an_isolated_timeout_process_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    class TimedOutProcess:
        pid = 9876
        calls = 0

        def communicate(self, timeout: int | None = None):
            self.calls += 1
            calls.append(
                {
                    "timeout": timeout,
                }
            )
            if self.calls == 1:
                raise subprocess.TimeoutExpired(
                    ["ethos", "status", "--json"],
                    timeout,
                    output="partial",
                    stderr="late",
                )
            return "partial", "late"

    def fake_popen(command: list[str], **kwargs: Any) -> TimedOutProcess:
        calls.append(
            {
                "command": command,
                "cwd": kwargs["cwd"],
                "text": kwargs["text"],
                "stdout": kwargs["stdout"],
                "stderr": kwargs["stderr"],
                "start_new_session": kwargs["start_new_session"],
            }
        )
        return TimedOutProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(os, "killpg", lambda *_args: None)

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
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "start_new_session": True,
        },
        {"timeout": 7},
        {"timeout": 1},
    ]
