from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NoReturn
from typing import cast

import pytest

import ethos.adapters.mutation.resolution.closeout.wcp.core as wcp_adapter
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPCloseoutExpectation
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPResponseError
from ethos.adapters.mutation.resolution.closeout.wcp.core import run_worktree_closeout_check
from ethos.adapters.mutation.resolution.closeout.wcp.core import validate_worktree_closeout_response

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_CHRONICLE_REF = "evidence/chronicle/ownerless-closeout/2026-07-22.md"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _expectation() -> WCPCloseoutExpectation:
    observation = {
        "lane_ref": "work/20260722-ownerless",
        "head": "1" * 40,
        "path": "/tmp/20260722-ownerless",
        "dirty": False,
    }
    decision = {
        "decision_id": _DECISION_ID,
        "observation": observation,
        "observation_digest": _digest(observation),
        "chronicle_ref": _CHRONICLE_REF,
        "chronicle_digest": "2" * 64,
    }
    return WCPCloseoutExpectation(
        branch="work/20260722-ownerless",
        path="/tmp/20260722-ownerless",
        head="1" * 40,
        lane_id="20260722-ownerless",
        lane_layout="canonical",
        executor_ref="agent:codex:thread:executor",
        decision_bytes=json.dumps(decision, sort_keys=True).encode(),
        observation=observation,
        chronicle_ref=_CHRONICLE_REF,
        accepted_branch="dev",
        accepted_head="3" * 40,
        accepted_tree="4" * 40,
    )


def _replace_decision(
    expected: WCPCloseoutExpectation,
    mutate: Callable[[dict[str, object]], None],
) -> WCPCloseoutExpectation:
    payload = json.loads(expected.decision_bytes)
    assert isinstance(payload, dict)
    mutate(payload)
    return replace(expected, decision_bytes=json.dumps(payload, sort_keys=True).encode())


def _runner() -> Callable[..., tuple[int, bytes]]:
    return cast("Callable[..., tuple[int, bytes]]", vars(wcp_adapter)["_run_bounded_output"])


class _FakeProcess:
    def __init__(
        self,
        *,
        poll_result: int | None = None,
        wait_error: BaseException | None = None,
    ) -> None:
        self.pid = 999_999_999
        self.stdout = None
        self.poll_result = poll_result
        self.wait_error = wait_error
        self.killed = False
        self.waited = False

    def poll(self) -> int | None:
        return self.poll_result

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        self.waited = True
        if self.wait_error is not None:
            raise self.wait_error
        return 0


def _raise_missing_process_group(_pid: int, _signal: int) -> NoReturn:
    message = "process group unavailable"
    raise OSError(message)


def test_wcp_response_rejects_a_non_object_payload() -> None:
    expected = _expectation()
    response = cast("Mapping[str, object]", [])

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response(response, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_invalid"
    assert raised.value.detail == "response"


def test_wcp_error_exposes_stable_gap_and_separate_detail() -> None:
    error = WCPResponseError("lane_resolution_wcp_timeout", "worktree-closeout-check")

    assert error.gap == "lane_resolution_wcp_timeout"
    assert error.detail == "worktree-closeout-check"
    assert str(error) == "lane_resolution_wcp_timeout:worktree-closeout-check"


@pytest.mark.parametrize(
    ("case", "detail"),
    [
        ("missing-decision-id", "expected.decision_bytes.decision_id"),
        ("empty-decision-id", "expected.decision_bytes.decision_id"),
        ("invalid-chronicle-digest", "expected.decision_bytes.chronicle_digest"),
    ],
)
def test_wcp_expectation_rejects_malformed_decision_bindings(case: str, detail: str) -> None:
    expected = _expectation()

    def mutate(payload: dict[str, object]) -> None:
        if case == "missing-decision-id":
            del payload["decision_id"]
        elif case == "empty-decision-id":
            payload["decision_id"] = ""
        else:
            payload["chronicle_digest"] = "G" * 64

    expected = _replace_decision(expected, mutate)

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response({}, expected=expected)

    expected_gap = "lane_resolution_wcp_expectation_invalid"
    if case != "invalid-chronicle-digest":
        expected_gap = (
            "lane_resolution_wcp_response_missing"
            if case == "missing-decision-id"
            else "lane_resolution_wcp_response_invalid"
        )
    assert raised.value.gap == expected_gap
    assert raised.value.detail == detail


def test_wcp_expectation_rejects_invalid_decision_json() -> None:
    expected = replace(_expectation(), decision_bytes=b"{")

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response({}, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_expectation_invalid"
    assert raised.value.detail == "decision_bytes.json"


def test_wcp_expectation_rejects_invalid_accepted_tree_oid() -> None:
    expected = replace(_expectation(), accepted_tree="G" * 40)

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response({}, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_expectation_invalid"
    assert raised.value.detail == "expected.accepted_tree"


def test_bounded_runner_returns_exact_success_output() -> None:
    returncode, output = _runner()(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'exact')"],
        timeout_seconds=2,
    )

    assert returncode == 0
    assert output == b"exact"


def test_bounded_runner_rejects_an_expired_deadline() -> None:
    remaining_or_timeout = cast(
        "Callable[[float, list[str], float], float]",
        vars(wcp_adapter)["_remaining_or_timeout"],
    )
    command = ["workstation", "repo-family"]

    with pytest.raises(subprocess.TimeoutExpired) as raised:
        remaining_or_timeout(-1, command, 2)

    assert raised.value.cmd == command
    assert raised.value.timeout == 2


def test_process_stop_falls_back_to_single_process_and_tolerates_wait_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop_process = cast(
        "Callable[[subprocess.Popen[bytes]], None]",
        vars(wcp_adapter)["_stop_process"],
    )
    monkeypatch.setattr(wcp_adapter.os, "killpg", _raise_missing_process_group)
    running = _FakeProcess(wait_error=subprocess.TimeoutExpired(["workstation"], 1))
    exited = _FakeProcess(poll_result=0, wait_error=OSError("already reaped"))

    stop_process(cast("subprocess.Popen[bytes]", running))
    stop_process(cast("subprocess.Popen[bytes]", exited))

    assert running.killed is True
    assert running.waited is True
    assert exited.killed is False
    assert exited.waited is True


def test_bounded_runner_maps_missing_stdout_pipe_to_unavailable_and_stops_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _FakeProcess()

    def spawn(*_args: object, **_kwargs: object) -> subprocess.Popen[bytes]:
        return cast("subprocess.Popen[bytes]", process)

    monkeypatch.setattr(wcp_adapter.subprocess, "Popen", spawn)
    monkeypatch.setattr(wcp_adapter.os, "killpg", _raise_missing_process_group)

    with pytest.raises(WCPResponseError) as raised:
        _runner()(["workstation"], timeout_seconds=2)

    assert raised.value.gap == "lane_resolution_wcp_unavailable"
    assert raised.value.detail == "OSError"
    assert process.killed is True
    assert process.waited is True


@pytest.mark.parametrize(
    ("failure", "expected_gap", "expected_detail"),
    [
        (
            WCPResponseError("lane_resolution_wcp_response_oversize", "64"),
            "lane_resolution_wcp_response_oversize",
            "64",
        ),
        (
            subprocess.TimeoutExpired(["workstation"], 2),
            "lane_resolution_wcp_timeout",
            "worktree-closeout-check",
        ),
    ],
)
def test_bounded_runner_preserves_fail_closed_pre_spawn_errors(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
    expected_gap: str,
    expected_detail: str,
) -> None:
    def fail_spawn(*_args: object, **_kwargs: object) -> NoReturn:
        raise failure

    monkeypatch.setattr(wcp_adapter.subprocess, "Popen", fail_spawn)

    with pytest.raises(WCPResponseError) as raised:
        _runner()(["workstation"], timeout_seconds=2)

    assert raised.value.gap == expected_gap
    assert raised.value.detail == expected_detail


def test_wcp_command_rejects_missing_and_wrong_kind_paths(tmp_path: Path) -> None:
    expected = _expectation()
    decision = tmp_path / "decision.json"
    decision.write_bytes(expected.decision_bytes)
    repo_file = tmp_path / "repo-file"
    repo_file.write_text("not a directory", encoding="utf-8")
    decision_directory = tmp_path / "decision-directory"
    decision_directory.mkdir()

    with pytest.raises(WCPResponseError) as missing_repo:
        run_worktree_closeout_check(
            repo=tmp_path / "missing-repo",
            decision_path=decision,
            expected=expected,
        )
    with pytest.raises(WCPResponseError) as wrong_repo_kind:
        run_worktree_closeout_check(repo=repo_file, decision_path=decision, expected=expected)
    with pytest.raises(WCPResponseError) as wrong_decision_kind:
        run_worktree_closeout_check(
            repo=tmp_path,
            decision_path=decision_directory,
            expected=expected,
        )

    assert (missing_repo.value.gap, missing_repo.value.detail) == (
        "lane_resolution_wcp_path_invalid",
        "repo",
    )
    assert (wrong_repo_kind.value.gap, wrong_repo_kind.value.detail) == (
        "lane_resolution_wcp_path_invalid",
        "repo",
    )
    assert (wrong_decision_kind.value.gap, wrong_decision_kind.value.detail) == (
        "lane_resolution_wcp_path_invalid",
        "decision",
    )


def test_wcp_command_rejects_an_unreadable_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _expectation()
    decision = tmp_path / "decision.json"
    decision.write_bytes(expected.decision_bytes)
    original_read_bytes = Path.read_bytes

    def fail_decision_read(path: Path) -> bytes:
        if path == decision:
            message = "decision unreadable"
            raise OSError(message)
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_decision_read)

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(repo=tmp_path, decision_path=decision, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_path_invalid"
    assert raised.value.detail == "decision"


def test_wcp_command_rejects_decision_snapshot_drift(tmp_path: Path) -> None:
    expected = _expectation()
    decision = tmp_path / "decision.json"
    decision.write_bytes(expected.decision_bytes + b"\n")

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(repo=tmp_path, decision_path=decision, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_decision_stale"
    assert raised.value.detail == "decision"


def test_wcp_command_rejects_a_nonzero_adapter_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _expectation()
    decision = tmp_path / "decision.json"
    decision.write_bytes(expected.decision_bytes)
    monkeypatch.setattr(wcp_adapter, "_run_bounded_output", lambda *_args, **_kwargs: (9, b""))

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(repo=tmp_path, decision_path=decision, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_rejected"
    assert raised.value.detail == "9"


def test_wcp_command_maps_a_missing_adapter_executable_to_unavailable(tmp_path: Path) -> None:
    expected = _expectation()
    decision = tmp_path / "decision.json"
    decision.write_bytes(expected.decision_bytes)

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(
            repo=tmp_path,
            decision_path=decision,
            expected=expected,
            workstation=(tmp_path / "missing-workstation").as_posix(),
        )

    assert raised.value.gap == "lane_resolution_wcp_unavailable"
    assert raised.value.detail == "FileNotFoundError"


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists():
        try:
            return stat.read_text(encoding="utf-8").split()[2] != "Z"
        except (IndexError, OSError):
            return True
    return True


def _wait_for_process_exit(pid: int) -> bool:
    deadline = time.monotonic() + 2
    while _process_is_running(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    return not _process_is_running(pid)


def test_bounded_runner_rejects_timeout() -> None:
    with pytest.raises(WCPResponseError) as raised:
        wcp_adapter._run_bounded_output(  # noqa: SLF001, RUF100 - bounded-runner contract
            [sys.executable, "-c", "import time; time.sleep(1)"],
            timeout_seconds=0.01,
        )

    assert raised.value.gap == "lane_resolution_wcp_timeout"


def test_bounded_runner_rejects_oversize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wcp_adapter, "_MAX_RESPONSE_BYTES", 32)

    with pytest.raises(WCPResponseError) as raised:
        wcp_adapter._run_bounded_output(  # noqa: SLF001, RUF100 - bounded-runner contract
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 64)"],
            timeout_seconds=2,
        )

    assert raised.value.gap == "lane_resolution_wcp_response_oversize"


@pytest.mark.parametrize(
    ("failure", "expected_gap"),
    [
        ("timeout", "lane_resolution_wcp_timeout"),
        ("oversize", "lane_resolution_wcp_response_oversize"),
    ],
)
def test_bounded_runner_terminates_descendant_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_gap: str,
) -> None:
    monkeypatch.setattr(wcp_adapter, "_MAX_RESPONSE_BYTES", 32)
    pid_path = tmp_path / "descendant.pid"
    trigger = (
        "sys.stdout.buffer.write(b'x' * 64); sys.stdout.flush(); time.sleep(60)"
        if failure == "oversize"
        else "raise SystemExit(0)"
    )
    startup_delay = "time.sleep(0.3); " if failure == "timeout" else ""
    script = (
        "import pathlib, subprocess, sys, time; "
        f"{startup_delay}"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        f"pathlib.Path({pid_path.as_posix()!r}).write_text(str(child.pid), encoding='utf-8'); "
        f"{trigger}"
    )

    with pytest.raises(WCPResponseError) as raised:
        wcp_adapter._run_bounded_output(  # noqa: SLF001, RUF100 - process-group contract
            [sys.executable, "-c", script],
            timeout_seconds=2,
        )

    assert raised.value.gap == expected_gap
    descendant_pid = int(pid_path.read_text(encoding="utf-8"))
    try:
        assert _wait_for_process_exit(descendant_pid)
    finally:
        if _process_is_running(descendant_pid):
            os.kill(descendant_pid, signal.SIGKILL)


def test_wcp_command_rejects_non_json_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    decision_path = tmp_path / "decision.json"
    expected = _expectation()
    decision_path.write_bytes(expected.decision_bytes)
    monkeypatch.setattr(wcp_adapter, "_run_bounded_output", lambda *_args, **_kwargs: (0, b"no"))

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(
            repo=repo,
            decision_path=decision_path,
            expected=expected,
        )

    assert raised.value.gap == "lane_resolution_wcp_response_invalid_json"


@pytest.mark.parametrize(
    "output",
    [
        pytest.param(b"1" * 5000, id="integer-conversion-limit"),
        pytest.param(b"[" * 400_000 + b"]" * 400_000, id="nesting-limit"),
    ],
)
def test_wcp_command_maps_json_parser_resource_errors_to_stable_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: bytes
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    decision_path = tmp_path / "decision.json"
    expected = _expectation()
    decision_path.write_bytes(expected.decision_bytes)
    monkeypatch.setattr(wcp_adapter, "_run_bounded_output", lambda *_args, **_kwargs: (0, output))

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(repo=repo, decision_path=decision_path, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_invalid_json"
