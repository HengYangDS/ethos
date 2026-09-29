"""Project human-readable decisions without losing failed output delivery."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

import ethos.surface.cli.output as output
from ethos.result import EthosResult


def test_human_output_projects_state_next_action_and_enforcement(capsys) -> None:
    result = EthosResult(
        command="plan",
        verdict="block",
        state="gapped",
        required_gaps=("repository_invalid",),
        next_action="repair the repository",
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "plan: gapped\nwhy: repository invalid\nnext: repair the repository\n"
    )
    with pytest.raises(SystemExit, match="1"):
        output.emit(result, json_output=False)


def test_human_output_exposes_every_blocker_and_decision_boundary(capsys) -> None:
    result = EthosResult(
        command="prove",
        verdict="block",
        state="gapped",
        required_gaps=(
            "openspec_active_change_ambiguous:greenfield-formation,installed-product",
            "required_tool_unavailable",
        ),
        next_action="openspec list --json",
        user_decision_required=True,
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "prove: gapped\n"
        "why: openspec active change ambiguous: greenfield-formation,installed-product\n"
        "why: required tool unavailable\n"
        "decision: human choice required\n"
        "next: openspec list --json\n"
    )


def test_human_output_uses_existing_diagnostic_message_for_a_block(capsys) -> None:
    result = EthosResult(
        command="status",
        verdict="block",
        state="gapped",
        diagnostics=(
            {
                "severity": "error",
                "code": "repository_binding_missing",
                "message": "Repository binding is missing.",
            },
        ),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == "status: gapped\nwhy: Repository binding is missing.\n"


def test_human_output_does_not_repeat_one_required_gap(capsys) -> None:
    result = EthosResult(
        command="prove",
        verdict="block",
        state="gapped",
        required_gaps=("openspec_official_cli_missing", "openspec_official_cli_missing"),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == "prove: gapped\nwhy: openspec official cli missing\n"


def test_human_output_keeps_distinct_diagnostics_without_codes(capsys) -> None:
    result = EthosResult(
        command="status",
        verdict="block",
        state="gapped",
        diagnostics=(
            {"severity": "warning", "message": "Policy observation unavailable."},
            {"severity": "error", "message": "Runtime binding unavailable."},
        ),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "status: gapped\nwhy: Policy observation unavailable.\nwhy: Runtime binding unavailable.\n"
    )


def test_human_output_keeps_distinct_messages_for_one_reason_code(capsys) -> None:
    result = EthosResult(
        command="prove",
        verdict="block",
        state="gapped",
        required_gaps=("gate_failed",),
        diagnostics=(
            {"severity": "warning", "code": "gate_failed", "message": "Unit tests failed."},
            {"severity": "error", "code": "gate_failed", "message": "Coverage is low."},
        ),
    )

    output.emit(result, json_output=False, enforce=False)

    assert capsys.readouterr().out == (
        "prove: gapped\nwhy: Unit tests failed.\nwhy: Coverage is low.\n"
    )


@pytest.mark.parametrize("error", [BrokenPipeError(), BlockingIOError()])
def test_output_pipe_failure_cannot_erase_a_blocked_verdict(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error: OSError
) -> None:
    monkeypatch.setattr(
        sys.stdout,
        "write",
        lambda _text: (_ for _ in ()).throw(error),
    )

    with pytest.raises(SystemExit) as exit_info:
        output.emit(
            EthosResult(
                command="status",
                verdict="block",
                state="gapped",
                required_gaps=("repository_invalid",),
            ),
            json_output=False,
        )

    assert exit_info.value.code == 1
    expected = "output_closed" if isinstance(error, BrokenPipeError) else "output_backpressure"
    assert expected in capsys.readouterr().err


def test_short_json_write_is_not_a_completed_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys.stdout, "write", lambda _text: 3)

    with pytest.raises(SystemExit) as exit_info:
        output.emit(EthosResult(command="status", verdict="pass", state="done"), json_output=True)

    assert exit_info.value.code == 1
    assert "output_partial" in capsys.readouterr().err


def test_flush_failure_after_write_is_not_reported_as_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FailingFlush:
        def write(self, text: str) -> int:
            return len(text)

        def flush(self) -> None:
            raise BrokenPipeError

    with monkeypatch.context() as scoped:
        scoped.setattr(sys, "stdout", FailingFlush())
        with pytest.raises(SystemExit) as exit_info:
            output.emit(
                EthosResult(command="status", verdict="pass", state="done"), json_output=True
            )

    assert exit_info.value.code == 1
    assert "output_closed" in capsys.readouterr().err


def test_real_full_nonblocking_pipe_preserves_one_failed_exit() -> None:
    read_fd, write_fd = os.pipe()
    os.set_blocking(write_fd, False)
    try:
        try:
            while True:
                os.write(write_fd, b"x" * 8192)
        except BlockingIOError:
            pass
        script = (
            "from ethos.result import EthosResult; "
            "from ethos.surface.cli.output import emit; "
            "emit(EthosResult(command='status', verdict='block', state='gapped', "
            "required_gaps=('probe',)), "
            "json_output=True)"
        )
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", script],
            stdout=write_fd,
            stderr=subprocess.PIPE,
        )
        os.close(write_fd)
        write_fd = -1
        _, stderr = process.communicate(timeout=5)
        assert process.returncode == 1
        assert b"output_backpressure" in stderr
        assert b"Exception ignored while flushing" not in stderr
    finally:
        if write_fd >= 0:
            os.close(write_fd)
        os.close(read_fd)
